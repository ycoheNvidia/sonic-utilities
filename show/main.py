import json
import os
import subprocess
import sys
import re

import click
import lazy_object_proxy
import utilities_common.cli as clicommon
from sonic_py_common import multi_asic
import utilities_common.multi_asic as multi_asic_util
from importlib import reload
from natsort import natsorted
from sonic_py_common import device_info
from swsscommon.swsscommon import SonicV2Connector, ConfigDBConnector
from tabulate import tabulate
from utilities_common import util_base
from utilities_common.db import Db
from datetime import datetime
import utilities_common.constants as constants
from utilities_common.general import load_db_config
from json.decoder import JSONDecodeError

# mock the redis for unit test purposes #
try:
    if os.environ["UTILITIES_UNIT_TESTING"] == "2":
        modules_path = os.path.join(os.path.dirname(__file__), "..")
        tests_path = os.path.join(modules_path, "tests")
        sys.path.insert(0, modules_path)
        sys.path.insert(0, tests_path)
        import mock_tables.dbconnector
    if os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] == "multi_asic":
        import mock_tables.mock_multi_asic
        reload(mock_tables.mock_multi_asic)
        reload(mock_tables.dbconnector)
        mock_tables.dbconnector.load_namespace_config()

except KeyError:
    pass

from . import acl
from . import bgp_common
from . import chassis_modules
from . import dropcounters
from . import fabric
from . import feature
from . import fgnhg
from . import flow_counters
from . import gearbox
from . import interfaces
from . import kdump
from . import kube
from . import muxcable
from . import nat
from . import platform
from . import processes
from . import reboot_cause
from . import sflow
from . import vlan
from . import vnet
from . import vxlan
from . import system_health
from . import warm_restart
from . import plugins
from . import syslog

# Global Variables
PLATFORM_JSON = 'platform.json'
HWSKU_JSON = 'hwsku.json'
PORT_STR = "Ethernet"

VLAN_SUB_INTERFACE_SEPARATOR = '.'

GEARBOX_TABLE_PHY_PATTERN = r"_GEARBOX_TABLE:phy:*"

COMMAND_TIMEOUT = 300

# To be enhanced. Routing-stack information should be collected from a global
# location (configdb?), so that we prevent the continous execution of this
# bash oneliner. To be revisited once routing-stack info is tracked somewhere.
def get_routing_stack():
    result = None
    command = "sudo docker ps | grep bgp | awk '{print$2}' | cut -d'-' -f3 | cut -d':' -f1 | head -n 1"

    try:
        stdout = subprocess.check_output(command, shell=True, text=True, timeout=COMMAND_TIMEOUT)
        result = stdout.rstrip('\n')
    except Exception as err:
        click.echo('Failed to get routing stack: {}'.format(err), err=True)

    return result


# Global Routing-Stack variable
routing_stack = get_routing_stack()

# Read given JSON file
def readJsonFile(fileName):
    try:
        with open(fileName) as f:
            result = json.load(f)
    except Exception as e:
        click.echo(str(e))
        raise click.Abort()
    return result

def run_command(command, display_cmd=False, return_cmd=False):
    if display_cmd:
        click.echo(click.style("Command: ", fg='cyan') + click.style(command, fg='green'))

    # No conversion needed for intfutil commands as it already displays
    # both SONiC interface name and alias name for all interfaces.
    if clicommon.get_interface_naming_mode() == "alias" and not command.startswith("intfutil"):
        clicommon.run_command_in_alias_mode(command)
        raise sys.exit(0)

    proc = subprocess.Popen(command, shell=True, text=True, stdout=subprocess.PIPE)

    while True:
        if return_cmd:
            output = proc.communicate()[0]
            return output
        output = proc.stdout.readline()
        if output == "" and proc.poll() is not None:
            break
        if output:
            click.echo(output.rstrip('\n'))

    rc = proc.poll()
    if rc != 0:
        sys.exit(rc)

def get_cmd_output(cmd):
    proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE)
    return proc.communicate()[0], proc.returncode

# Lazy global class instance for SONiC interface name to alias conversion
iface_alias_converter = lazy_object_proxy.Proxy(lambda: clicommon.InterfaceAliasConverter())

#
# Display all storm-control data 
#
def display_storm_all():
    """ Show storm-control """
    header = ['Interface Name', 'Storm Type', 'Rate (kbps)']
    body = []

    config_db = ConfigDBConnector()
    config_db.connect()

    table = config_db.get_table('PORT_STORM_CONTROL')

    #To avoid further looping below
    if not table:
        return

    sorted_table = natsorted(table)

    for storm_key in sorted_table:
        interface_name = storm_key[0]
        storm_type = storm_key[1]
        #interface_name, storm_type = storm_key.split(':')
        data = config_db.get_entry('PORT_STORM_CONTROL', storm_key)

        if not data:
            return

        kbps = data['kbps']

        body.append([interface_name, storm_type, kbps])

    click.echo(tabulate(body, header, tablefmt="grid"))

#
# Get storm-control configurations per interface append to body
#
def get_storm_interface(intf, body):
    storm_type_list = ['broadcast','unknown-unicast','unknown-multicast']

    config_db = ConfigDBConnector()
    config_db.connect()

    table = config_db.get_table('PORT_STORM_CONTROL')

    #To avoid further looping below
    if not table:
        return

    for storm_type in storm_type_list:
        storm_key = intf + '|' + storm_type
        data = config_db.get_entry('PORT_STORM_CONTROL', storm_key)

        if data:
            kbps = data['kbps']
            body.append([intf, storm_type, kbps])

#
# Display storm-control data of given interface
#
def display_storm_interface(intf):
    """ Show storm-control """

    storm_type_list = ['broadcast','unknown-unicast','unknown-multicast']

    header = ['Interface Name', 'Storm Type', 'Rate (kbps)']
    body = []

    config_db = ConfigDBConnector()
    config_db.connect()

    table = config_db.get_table('PORT_STORM_CONTROL')

    #To avoid further looping below
    if not table:
        return

    for storm_type in storm_type_list:
        storm_key = intf + '|' + storm_type
        data = config_db.get_entry('PORT_STORM_CONTROL', storm_key)

        if data:
            kbps = data['kbps']
            body.append([intf, storm_type, kbps])

    click.echo(tabulate(body, header, tablefmt="grid"))

def connect_config_db():
    """
    Connects to config_db
    """
    config_db = ConfigDBConnector()
    config_db.connect()
    return config_db

def is_gearbox_configured():
    """
    Checks whether Gearbox is configured or not
    """
    app_db = SonicV2Connector()
    app_db.connect(app_db.APPL_DB)

    keys = app_db.keys(app_db.APPL_DB, '*')

    # If any _GEARBOX_TABLE:phy:* records present in APPL_DB, then the gearbox is configured
    if any(re.match(GEARBOX_TABLE_PHY_PATTERN, key) for key in keys):
        return True
    else:
        return False

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])

#
# 'cli' group (root group)
#

# This is our entrypoint - the main "show" command
# TODO: Consider changing function name to 'show' for better understandability
@click.group(cls=clicommon.AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx):
    """SONiC command line - 'show' command"""

    # Load database config files
    load_db_config()
    ctx.obj = Db()


# Add groups from other modules
cli.add_command(acl.acl)
cli.add_command(chassis_modules.chassis)
cli.add_command(dropcounters.dropcounters)
cli.add_command(fabric.fabric)
cli.add_command(feature.feature)
cli.add_command(fgnhg.fgnhg)
cli.add_command(flow_counters.flowcnt_route)
cli.add_command(flow_counters.flowcnt_trap)
cli.add_command(kdump.kdump)
cli.add_command(interfaces.interfaces)
cli.add_command(kdump.kdump)
cli.add_command(kube.kubernetes)
cli.add_command(muxcable.muxcable)
cli.add_command(nat.nat)
cli.add_command(platform.platform)
cli.add_command(processes.processes)
cli.add_command(reboot_cause.reboot_cause)
cli.add_command(sflow.sflow)
cli.add_command(vlan.vlan)
cli.add_command(vnet.vnet)
cli.add_command(vxlan.vxlan)
cli.add_command(system_health.system_health)
cli.add_command(warm_restart.warm_restart)

# syslog module
cli.add_command(syslog.syslog)

# Add greabox commands only if GEARBOX is configured
if is_gearbox_configured():
    cli.add_command(gearbox.gearbox)


#
# 'vrf' command ("show vrf")
#

def get_interface_bind_to_vrf(config_db, vrf_name):
    """Get interfaces belong to vrf
    """
    tables = ['INTERFACE', 'PORTCHANNEL_INTERFACE', 'VLAN_INTERFACE', 'LOOPBACK_INTERFACE', 'VLAN_SUB_INTERFACE']
    data = []
    for table_name in tables:
        interface_dict = config_db.get_table(table_name)
        if interface_dict:
            for interface in interface_dict:
                if 'vrf_name' in interface_dict[interface] and vrf_name == interface_dict[interface]['vrf_name']:
                    data.append(interface)
    return data

@cli.command()
@click.argument('vrf_name', required=False)
def vrf(vrf_name):
    """Show vrf config"""
    config_db = ConfigDBConnector()
    config_db.connect()
    header = ['VRF', 'Interfaces']
    body = []
    vrf_dict = config_db.get_table('VRF')
    if vrf_dict:
        vrfs = []
        if vrf_name is None:
            vrfs = list(vrf_dict.keys())
        elif vrf_name in vrf_dict:
            vrfs = [vrf_name]
        for vrf in vrfs:
            intfs = get_interface_bind_to_vrf(config_db, vrf)
            intfs = natsorted(intfs)
            if len(intfs) == 0:
                body.append([vrf, ""])
            else:
                body.append([vrf, intfs[0]])
                for intf in intfs[1:]:
                    body.append(["", intf])
    click.echo(tabulate(body, header))

#
# 'events' command ("show event-counters")
#

@cli.command()
def event_counters():
    """Show events counter"""
    # dump keys as formatted
    counters_db = SonicV2Connector(host='127.0.0.1')
    counters_db.connect(counters_db.COUNTERS_DB, retry_on=False)

    header = ['name', 'count']
    keys = counters_db.keys(counters_db.COUNTERS_DB, 'COUNTERS_EVENTS*')
    table = []

    for key in natsorted(keys):
        key_list = key.split(':')
        data_dict = counters_db.get_all(counters_db.COUNTERS_DB, key)
        table.append((key_list[1], data_dict["value"]))

    if table:
        click.echo(tabulate(table, header, tablefmt='simple', stralign='right'))
    else:
        click.echo('No data available in COUNTERS_EVENTS\n')


#
# 'arp' command ("show arp")
#

@cli.command()
@click.argument('ipaddress', required=False)
@click.option('-if', '--iface')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def arp(ipaddress, iface, verbose):
    """Show IP ARP table"""
    cmd = "nbrshow -4"

    if ipaddress is not None:
        cmd += " -ip {}".format(ipaddress)

    if iface is not None:
        if clicommon.get_interface_naming_mode() == "alias":
            if not ((iface.startswith("PortChannel")) or
                    (iface.startswith("eth"))):
                iface = iface_alias_converter.alias_to_name(iface)

        cmd += " -if {}".format(iface)

    run_command(cmd, display_cmd=verbose)

#
# 'ndp' command ("show ndp")
#

@cli.command()
@click.argument('ip6address', required=False)
@click.option('-if', '--iface')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ndp(ip6address, iface, verbose):
    """Show IPv6 Neighbour table"""
    cmd = "nbrshow -6"

    if ip6address is not None:
        cmd += " -ip {}".format(ip6address)

    if iface is not None:
        cmd += " -if {}".format(iface)

    run_command(cmd, display_cmd=verbose)

def is_mgmt_vrf_enabled(ctx):
    """Check if management VRF is enabled"""
    if ctx.invoked_subcommand is None:
        cmd = 'sonic-cfggen -d --var-json "MGMT_VRF_CONFIG"'

        p = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try :
            mvrf_dict = json.loads(p.stdout.read())
        except ValueError:
            print("MGMT_VRF_CONFIG is not present.")
            return False

        # if the mgmtVrfEnabled attribute is configured, check the value
        # and return True accordingly.
        if 'mgmtVrfEnabled' in mvrf_dict['vrf_global']:
            if (mvrf_dict['vrf_global']['mgmtVrfEnabled'] == "true"):
                #ManagementVRF is enabled. Return True.
                return True

    return False

#
# 'storm-control' group 
# "show storm-control [interface <interface>]"
#
@cli.group('storm-control', invoke_without_command=True)
@click.option('--namespace',
              '-n',
              'namespace',
              default=None,
              type=str,
              show_default=True,
              help='Namespace name or all',
              callback=multi_asic_util.multi_asic_namespace_validation_callback)
@click.option('--display', '-d', 'display', default=None, show_default=False, type=str, help='all|frontend')
@click.pass_context
def storm_control(ctx, namespace, display):
    """ Show storm-control """
    header = ['Interface Name', 'Storm Type', 'Rate (kbps)']
    body = []
    if ctx.invoked_subcommand is None:
        if namespace is None:
            display_storm_all()
        else:
            interfaces = multi_asic.multi_asic_get_ip_intf_from_ns(namespace)
            for intf in interfaces:
                get_storm_interface(intf, body)
            click.echo(tabulate(body, header, tablefmt="grid"))

@storm_control.command('interface')
@click.argument('interface', metavar='<interface>',required=True)
def interface(interface, namespace, display):
    if multi_asic.is_multi_asic() and namespace not in multi_asic.get_namespace_list():
        ctx = click.get_current_context()
        ctx.fail('-n/--namespace option required. provide namespace from list {}'.format(multi_asic.get_namespace_list()))
    if interface:
        display_storm_interface(interface)

#
# 'mgmt-vrf' group ("show mgmt-vrf ...")
#

@cli.group('mgmt-vrf', invoke_without_command=True)
@click.argument('routes', required=False, type=click.Choice(["routes"]))
@click.pass_context
def mgmt_vrf(ctx,routes):
    """Show management VRF attributes"""

    if is_mgmt_vrf_enabled(ctx) is False:
        click.echo("\nManagementVRF : Disabled")
        return
    else:
        if routes is None:
            click.echo("\nManagementVRF : Enabled")
            click.echo("\nManagement VRF interfaces in Linux:")
            cmd = "ip -d link show mgmt"
            run_command(cmd)
            cmd = "ip link show vrf mgmt"
            run_command(cmd)
        else:
            click.echo("\nRoutes in Management VRF Routing Table:")
            cmd = "ip route show table 5000"
            run_command(cmd)

#
# 'management_interface' group ("show management_interface ...")
#

@cli.group(name='management_interface', cls=clicommon.AliasedGroup)
def management_interface():
    """Show management interface parameters"""
    pass

# 'address' subcommand ("show management_interface address")
@management_interface.command()
def address ():
    """Show IP address configured for management interface"""

    config_db = ConfigDBConnector()
    config_db.connect()

    # Fetching data from config_db for MGMT_INTERFACE
    mgmt_ip_data = config_db.get_table('MGMT_INTERFACE')
    for key in natsorted(list(mgmt_ip_data.keys())):
        click.echo("Management IP address = {0}".format(key[1]))
        click.echo("Management Network Default Gateway = {0}".format(mgmt_ip_data[key]['gwaddr']))

#
# 'snmpagentaddress' group ("show snmpagentaddress ...")
#

@cli.group('snmpagentaddress', invoke_without_command=True)
@click.pass_context
def snmpagentaddress (ctx):
    """Show SNMP agent listening IP address configuration"""
    config_db = ConfigDBConnector()
    config_db.connect()
    agenttable = config_db.get_table('SNMP_AGENT_ADDRESS_CONFIG')

    header = ['ListenIP', 'ListenPort', 'ListenVrf']
    body = []
    for agent in agenttable:
        body.append([agent[0], agent[1], agent[2]])
    click.echo(tabulate(body, header))

#
# 'snmptrap' group ("show snmptrap ...")
#

@cli.group('snmptrap', invoke_without_command=True)
@click.pass_context
def snmptrap (ctx):
    """Show SNMP agent Trap server configuration"""
    config_db = ConfigDBConnector()
    config_db.connect()
    traptable = config_db.get_table('SNMP_TRAP_CONFIG')

    header = ['Version', 'TrapReceiverIP', 'Port', 'VRF', 'Community']
    body = []
    for row in traptable:
        if row == "v1TrapDest":
            ver=1
        elif row == "v2TrapDest":
            ver=2
        else:
            ver=3
        body.append([ver, traptable[row]['DestIp'], traptable[row]['DestPort'], traptable[row]['vrf'], traptable[row]['Community']])
    click.echo(tabulate(body, header))


#
# 'subinterfaces' group ("show subinterfaces ...")
#

@cli.group(cls=clicommon.AliasedGroup)
def subinterfaces():
    """Show details of the sub port interfaces"""
    pass

# 'subinterfaces' subcommand ("show subinterfaces status")
@subinterfaces.command()
@click.argument('subinterfacename', type=str, required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def status(subinterfacename, verbose):
    """Show sub port interface status information"""
    cmd = "intfutil -c status"

    if subinterfacename is not None:
        sub_intf_sep_idx = subinterfacename.find(VLAN_SUB_INTERFACE_SEPARATOR)
        if sub_intf_sep_idx == -1:
            print("Invalid sub port interface name")
            return

        if clicommon.get_interface_naming_mode() == "alias":
            subinterfacename = iface_alias_converter.alias_to_name(subinterfacename)

        cmd += " -i {}".format(subinterfacename)
    else:
        cmd += " -i subport"
    run_command(cmd, display_cmd=verbose)

#
# 'pfc' group ("show pfc ...")
#

@cli.group(cls=clicommon.AliasedGroup)
def pfc():
    """Show details of the priority-flow-control (pfc) """
    pass

# 'counters' subcommand ("show interfaces pfccounters")
@pfc.command()
@multi_asic_util.multi_asic_click_options
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def counters(namespace, display, verbose):
    """Show pfc counters"""

    cmd = "pfcstat -s {}".format(display)
    if namespace is not None:
        cmd += " -n {}".format(namespace)

    run_command(cmd, display_cmd=verbose)

@pfc.command()
@click.argument('interface', type=click.STRING, required=False)
def priority(interface):
    """Show pfc priority"""
    cmd = 'pfc show priority'
    if interface is not None and clicommon.get_interface_naming_mode() == "alias":
        interface = iface_alias_converter.alias_to_name(interface)

    if interface is not None:
        cmd += ' {0}'.format(interface)

    run_command(cmd)

@pfc.command()
@click.argument('interface', type=click.STRING, required=False)
def asymmetric(interface):
    """Show asymmetric pfc"""
    cmd = 'pfc show asymmetric'
    if interface is not None and clicommon.get_interface_naming_mode() == "alias":
        interface = iface_alias_converter.alias_to_name(interface)

    if interface is not None:
        cmd += ' {0}'.format(interface)

    run_command(cmd)

# 'pfcwd' subcommand ("show pfcwd...")
@cli.group(cls=clicommon.AliasedGroup)
def pfcwd():
    """Show details of the pfc watchdog """
    pass

@pfcwd.command()
@multi_asic_util.multi_asic_click_options
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def config(namespace, display, verbose):
    """Show pfc watchdog config"""

    cmd = "pfcwd show config -d {}".format(display)
    if namespace is not None:
        cmd += " -n {}".format(namespace)

    run_command(cmd, display_cmd=verbose)

@pfcwd.command()
@multi_asic_util.multi_asic_click_options
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def stats(namespace, display, verbose):
    """Show pfc watchdog stats"""

    cmd = "pfcwd show stats -d {}".format(display)
    if namespace is not None:
        cmd += " -n {}".format(namespace)

    run_command(cmd, display_cmd=verbose)

#
# 'watermark' group ("show watermark telemetry interval")
#

@cli.group(cls=clicommon.AliasedGroup)
def watermark():
    """Show details of watermark """
    pass

@watermark.group()
def telemetry():
    """Show watermark telemetry info"""
    pass

@telemetry.command('interval')
def show_tm_interval():
    """Show telemetry interval"""
    command = 'watermarkcfg --show-interval'
    run_command(command)


#
# 'queue' group ("show queue ...")
#

@cli.group(cls=clicommon.AliasedGroup)
def queue():
    """Show details of the queues """
    pass

# 'counters' subcommand ("show queue counters")
@queue.command()
@click.argument('interfacename', required=False)
@multi_asic_util.multi_asic_click_options
@click.option('--verbose', is_flag=True, help="Enable verbose output")
@click.option('--json', is_flag=True, help="JSON output")
@click.option('--voq', is_flag=True, help="VOQ counters")
def counters(interfacename, namespace, display, verbose, json, voq):
    """Show queue counters"""

    cmd = "queuestat"

    if interfacename is not None:
        if clicommon.get_interface_naming_mode() == "alias":
            interfacename = iface_alias_converter.alias_to_name(interfacename)

    if interfacename is not None:
        cmd += " -p {}".format(interfacename)

    if namespace is not None:
        cmd += " -n {}".format(namespace)

    if json:
        cmd += " -j"

    if voq:
        cmd += " -V"

    run_command(cmd, display_cmd=verbose)

#
# 'watermarks' subgroup ("show queue watermarks ...")
#

@queue.group()
def watermark():
    """Show user WM for queues"""
    pass

# 'unicast' subcommand ("show queue watermarks unicast")
@watermark.command('unicast')
def wm_q_uni():
    """Show user WM for unicast queues"""
    command = 'watermarkstat -t q_shared_uni'
    run_command(command)

# 'multicast' subcommand ("show queue watermarks multicast")
@watermark.command('multicast')
def wm_q_multi():
    """Show user WM for multicast queues"""
    command = 'watermarkstat -t q_shared_multi'
    run_command(command)

# 'all' subcommand ("show queue watermarks all")
@watermark.command('all')
def wm_q_all():
    """Show user WM for all queues"""
    command = 'watermarkstat -t q_shared_all'
    run_command(command)

#
# 'persistent-watermarks' subgroup ("show queue persistent-watermarks ...")
#

@queue.group(name='persistent-watermark')
def persistent_watermark():
    """Show persistent WM for queues"""
    pass

# 'unicast' subcommand ("show queue persistent-watermarks unicast")
@persistent_watermark.command('unicast')
def pwm_q_uni():
    """Show persistent WM for unicast queues"""
    command = 'watermarkstat -p -t q_shared_uni'
    run_command(command)

# 'multicast' subcommand ("show queue persistent-watermarks multicast")
@persistent_watermark.command('multicast')
def pwm_q_multi():
    """Show persistent WM for multicast queues"""
    command = 'watermarkstat -p -t q_shared_multi'
    run_command(command)

# 'all' subcommand ("show queue persistent-watermarks all")
@persistent_watermark.command('all')
def pwm_q_all():
    """Show persistent WM for all queues"""
    command = 'watermarkstat -p -t q_shared_all'
    run_command(command)

#
# 'priority-group' group ("show priority-group ...")
#

@cli.group(name='priority-group', cls=clicommon.AliasedGroup)
def priority_group():
    """Show details of the PGs """

@priority_group.group()
def watermark():
    """Show priority-group user WM"""
    pass

@watermark.command('headroom')
def wm_pg_headroom():
    """Show user headroom WM for pg"""
    command = 'watermarkstat -t pg_headroom'
    run_command(command)

@watermark.command('shared')
def wm_pg_shared():
    """Show user shared WM for pg"""
    command = 'watermarkstat -t pg_shared'
    run_command(command)

@priority_group.group()
def drop():
    """Show priority-group"""
    pass

@drop.command('counters')
def pg_drop_counters():
    """Show dropped packets for priority-group"""
    command = 'pg-drop -c show'
    run_command(command)

@priority_group.group(name='persistent-watermark')
def persistent_watermark():
    """Show priority-group persistent WM"""
    pass

@persistent_watermark.command('headroom')
def pwm_pg_headroom():
    """Show persistent headroom WM for pg"""
    command = 'watermarkstat -p -t pg_headroom'
    run_command(command)

@persistent_watermark.command('shared')
def pwm_pg_shared():
    """Show persistent shared WM for pg"""
    command = 'watermarkstat -p -t pg_shared'
    run_command(command)


#
# 'buffer_pool' group ("show buffer_pool ...")
#

@cli.group(name='buffer_pool', cls=clicommon.AliasedGroup)
def buffer_pool():
    """Show details of the buffer pools"""

@buffer_pool.command('watermark')
def wm_buffer_pool():
    """Show user WM for buffer pools"""
    command = 'watermarkstat -t buffer_pool'
    run_command(command)

@buffer_pool.command('persistent-watermark')
def pwm_buffer_pool():
    """Show persistent WM for buffer pools"""
    command = 'watermarkstat -p -t buffer_pool'
    run_command(command)


#
# 'headroom-pool' group ("show headroom-pool ...")
#

@cli.group(name='headroom-pool', cls=clicommon.AliasedGroup)
def headroom_pool():
    """Show details of headroom pool"""

@headroom_pool.command('watermark')
def wm_headroom_pool():
    """Show user WM for headroom pool"""
    command = 'watermarkstat -t headroom_pool'
    run_command(command)

@headroom_pool.command('persistent-watermark')
def pwm_headroom_pool():
    """Show persistent WM for headroom pool"""
    command = 'watermarkstat -p -t headroom_pool'
    run_command(command)


#
# 'mac' command ("show mac ...")
#

@cli.group(cls=clicommon.AliasedGroup, invoke_without_command="true")
@click.pass_context
@click.option('-v', '--vlan')
@click.option('-p', '--port')
@click.option('-a', '--address')
@click.option('-t', '--type')
@click.option('-c', '--count', is_flag=True)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def mac(ctx, vlan, port, address, type, count, verbose):
    """Show MAC (FDB) entries"""

    if ctx.invoked_subcommand is not None:
        return

    cmd = "fdbshow"

    if vlan is not None:
        cmd += " -v {}".format(vlan)

    if port is not None:
        cmd += " -p {}".format(port)

    if address is not None:
        cmd += " -a {}".format(address)

    if type is not None:
        cmd += " -t {}".format(type)

    if count:
        cmd += " -c"

    run_command(cmd, display_cmd=verbose)

@mac.command('aging-time')
@click.pass_context
def aging_time(ctx):
    app_db = SonicV2Connector()
    app_db.connect(app_db.APPL_DB)
    table = "SWITCH_TABLE*"
    keys = app_db.keys(app_db.APPL_DB, table)

    if not keys:
        click.echo("Aging time not configured for the switch")
        return

    for key in keys:
        fdb_aging_time = app_db.get(app_db.APPL_DB, key, 'fdb_aging_time')
        if fdb_aging_time is not None:
            click.echo("Aging time for {} is {} seconds".format(key.split(':')[-1], fdb_aging_time))
        else:
            click.echo("Aging time not configured for the {}".format(key.split(':')[-1]))
#
# 'show route-map' command ("show route-map")
#

@cli.command('route-map')
@click.argument('route_map_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def route_map(route_map_name, verbose):
    """show route-map"""
    cmd = 'sudo {} -c "show route-map'.format(constants.RVTYSH_COMMAND)
    if route_map_name is not None:
        cmd += ' {}'.format(route_map_name)
    cmd += '"'
    run_command(cmd, display_cmd=verbose)

#
# 'ip' group ("show ip ...")
#

# This group houses IP (i.e., IPv4) commands and subgroups
@cli.group(cls=clicommon.AliasedGroup)
def ip():
    """Show IP (IPv4) commands"""
    pass


#
# 'show ip interfaces' command
#
# Display all interfaces with master, an IPv4 address, admin/oper states, their BGP neighbor name and peer ip.
# Addresses from all scopes are included. Interfaces with no addresses are
# excluded.
#

@ip.group(invoke_without_command=True)
@multi_asic_util.multi_asic_click_options
@click.pass_context
def interfaces(ctx, namespace, display):
    if ctx.invoked_subcommand is None:
        cmd = "sudo ipintutil -a ipv4"
        if namespace is not None:
            cmd += " -n {}".format(namespace)

        cmd += " -d {}".format(display)
        clicommon.run_command(cmd)

#
# 'show ip interfaces loopback-action' command
#

@interfaces.command()
def loopback_action():
    """show ip interfaces loopback-action"""
    config_db = ConfigDBConnector()
    config_db.connect()
    header = ['Interface', 'Action']
    body = []

    if_tbl = config_db.get_table('INTERFACE')
    vlan_if_tbl = config_db.get_table('VLAN_INTERFACE')
    po_if_tbl = config_db.get_table('PORTCHANNEL_INTERFACE')
    sub_if_tbl = config_db.get_table('VLAN_SUB_INTERFACE')

    all_tables = {}
    for tbl in [if_tbl, vlan_if_tbl, po_if_tbl, sub_if_tbl]:
        all_tables.update(tbl)

    if all_tables:
        ifs_action = []
        ifs = list(all_tables.keys())
        for iface in ifs:
            if 'loopback_action' in all_tables[iface]:
                action = all_tables[iface]['loopback_action']
                ifs_action.append([iface, action])
        body = natsorted(ifs_action)
    click.echo(tabulate(body, header))

#
# 'route' subcommand ("show ip route")
#

@ip.command()
@click.argument('args', metavar='[IPADDRESS] [vrf <vrf_name>] [...]', nargs=-1, required=False)
@click.option('--display', '-d', 'display', default=None, show_default=False, type=str, help='all|frontend')
@click.option('--namespace', '-n', 'namespace', default=None, type=str, show_default=False, help='Namespace name or all')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def route(args, namespace, display, verbose):
    """Show IP (IPv4) routing table"""
    # Call common handler to handle the show ip route cmd
    bgp_common.show_routes(args, namespace, display, verbose, "ip")

#
# 'prefix-list' subcommand ("show ip prefix-list")
#

@ip.command('prefix-list')
@click.argument('prefix_list_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def prefix_list(prefix_list_name, verbose):
    """show ip prefix-list"""
    cmd = 'sudo {} -c "show ip prefix-list'.format(constants.RVTYSH_COMMAND)
    if prefix_list_name is not None:
        cmd += ' {}'.format(prefix_list_name)
    cmd += '"'
    run_command(cmd, display_cmd=verbose)


# 'protocol' command
@ip.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def protocol(verbose):
    """Show IPv4 protocol information"""
    cmd = 'sudo {} -c "show ip protocol"'.format(constants.RVTYSH_COMMAND)
    run_command(cmd, display_cmd=verbose)

#
# 'fib' subcommand ("show ip fib")
#
@ip.command()
@click.argument('ipaddress', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def fib(ipaddress, verbose):
    """Show IP FIB table"""
    cmd = "fibshow -4"
    if ipaddress is not None:
        cmd += " -ip {}".format(ipaddress)
    run_command(cmd, display_cmd=verbose)


#
# 'ipv6' group ("show ipv6 ...")
#

# This group houses IPv6-related commands and subgroups
@cli.group(cls=clicommon.AliasedGroup)
def ipv6():
    """Show IPv6 commands"""
    pass

#
# 'prefix-list' subcommand ("show ipv6 prefix-list")
#

@ipv6.command('prefix-list')
@click.argument('prefix_list_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def prefix_list(prefix_list_name, verbose):
    """show ip prefix-list"""
    cmd = 'sudo {} -c "show ipv6 prefix-list'.format(constants.RVTYSH_COMMAND)
    if prefix_list_name is not None:
        cmd += ' {}'.format(prefix_list_name)
    cmd += '"'
    run_command(cmd, display_cmd=verbose)



#
# 'show ipv6 interfaces' command
#
# Display all interfaces with master, an IPv6 address, admin/oper states, their BGP neighbor name and peer ip.
# Addresses from all scopes are included. Interfaces with no addresses are
# excluded.
#
@ipv6.command()
@multi_asic_util.multi_asic_click_options
def interfaces(namespace, display):
    cmd = "sudo ipintutil -a ipv6"

    if namespace is not None:
        cmd += " -n {}".format(namespace)

    cmd += " -d {}".format(display)

    clicommon.run_command(cmd)


#
# 'route' subcommand ("show ipv6 route")
#

@ipv6.command()
@click.argument('args', metavar='[IPADDRESS] [vrf <vrf_name>] [...]', nargs=-1, required=False)
@click.option('--display', '-d', 'display', default=None, show_default=False, type=str, help='all|frontend')
@click.option('--namespace', '-n', 'namespace', default=None, type=str, show_default=False, help='Namespace name or all')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def route(args, namespace, display, verbose):
    """Show IPv6 routing table"""
    # Call common handler to handle the show ipv6 route cmd
    bgp_common.show_routes(args, namespace, display, verbose, "ipv6")


# 'protocol' command
@ipv6.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def protocol(verbose):
    """Show IPv6 protocol information"""
    cmd = 'sudo {} -c "show ipv6 protocol"'.format(constants.RVTYSH_COMMAND)
    run_command(cmd, display_cmd=verbose)

#
# Inserting BGP functionality into cli's show parse-chain.
# BGP commands are determined by the routing-stack being elected.
#
if routing_stack == "quagga":
    from .bgp_quagga_v4 import bgp
    ip.add_command(bgp)
    from .bgp_quagga_v6 import bgp
    ipv6.add_command(bgp)
elif routing_stack == "frr":
    from .bgp_frr_v4 import bgp
    ip.add_command(bgp)
    from .bgp_frr_v6 import bgp
    ipv6.add_command(bgp)

#
# 'link-local-mode' subcommand ("show ipv6 link-local-mode")
#

@ipv6.command('link-local-mode')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def link_local_mode(verbose):
    """show ipv6 link-local-mode"""
    header = ['Interface Name', 'Mode']
    body = []
    tables = ['PORT', 'PORTCHANNEL', 'VLAN']
    config_db = ConfigDBConnector()
    config_db.connect()
    interface = ""

    for table in tables:
        if table == "PORT":
            interface = "INTERFACE"
        elif table == "PORTCHANNEL":
            interface = "PORTCHANNEL_INTERFACE"
        elif table == "VLAN":
            interface = "VLAN_INTERFACE"

        port_dict = config_db.get_table(table)
        interface_dict = config_db.get_table(interface)
        link_local_data = {}

        for port in port_dict.keys():
            if port not in interface_dict:
                body.append([port, 'Disabled'])
            elif interface_dict:
                value = interface_dict[port]
                if 'ipv6_use_link_local_only' in value:
                    link_local_data[port] = interface_dict[port]['ipv6_use_link_local_only']
                    if link_local_data[port] == 'enable':
                        body.append([port, 'Enabled'])
                    else:
                        body.append([port, 'Disabled'])
                else:
                    body.append([port, 'Disabled'])

    click.echo(tabulate(body, header, tablefmt="grid"))

#
# 'fib' subcommand ("show ipv6 fib")
#
@ipv6.command()
@click.argument('ipaddress', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def fib(ipaddress, verbose):
    """Show IP FIB table"""
    cmd = "fibshow -6"
    if ipaddress is not None:
        cmd += " -ip {}".format(ipaddress)
    run_command(cmd, display_cmd=verbose)

#
# 'lldp' group ("show lldp ...")
#

@cli.group(cls=clicommon.AliasedGroup)
def lldp():
    """Show LLDP information"""
    pass

# Default 'lldp' command (called if no subcommands or their aliases were passed)
@lldp.command()
@click.argument('interfacename', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def neighbors(interfacename, verbose):
    """Show LLDP neighbors"""
    cmd = "sudo lldpshow -d"

    if interfacename is not None:
        if clicommon.get_interface_naming_mode() == "alias":
            interfacename = iface_alias_converter.alias_to_name(interfacename)

        cmd += " -p {}".format(interfacename)

    run_command(cmd, display_cmd=verbose)

# 'table' subcommand ("show lldp table")
@lldp.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def table(verbose):
    """Show LLDP neighbors in tabular format"""
    cmd = "sudo lldpshow"
    run_command(cmd, display_cmd=verbose)


#
# 'logging' command ("show logging")
#

@cli.command()
@click.argument('process', required=False)
@click.option('-l', '--lines')
@click.option('-f', '--follow', is_flag=True)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def logging(process, lines, follow, verbose):
    """Show system log"""
    if os.path.exists("/var/log.tmpfs"):
        log_path = "/var/log.tmpfs"
    else:
        log_path = "/var/log"
    if follow:
        cmd = "sudo tail -F {}/syslog".format(log_path)
        run_command(cmd, display_cmd=verbose)
    else:
        if os.path.isfile("{}/syslog.1".format(log_path)):
            cmd = "sudo cat {}/syslog.1 {}/syslog".format(log_path, log_path)
        else:
            cmd = "sudo cat {}/syslog".format(log_path)

        if process is not None:
            cmd += " | grep '{}'".format(process)

        if lines is not None:
            cmd += " | tail -{}".format(lines)

        run_command(cmd, display_cmd=verbose)


#
# 'version' command ("show version")
#

@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def version(verbose):
    """Show version information"""
    version_info = device_info.get_sonic_version_info()
    platform_info = device_info.get_platform_info()
    chassis_info = platform.get_chassis_info()

    sys_uptime_cmd = "uptime"
    sys_uptime = subprocess.Popen(sys_uptime_cmd, shell=True, text=True, stdout=subprocess.PIPE)

    sys_date = datetime.now()

    click.echo("\nSONiC Software Version: SONiC.{}".format(version_info['build_version']))
    click.echo("Distribution: Debian {}".format(version_info['debian_version']))
    click.echo("Kernel: {}".format(version_info['kernel_version']))
    click.echo("Build commit: {}".format(version_info['commit_id']))
    click.echo("Build date: {}".format(version_info['build_date']))
    click.echo("Built by: {}".format(version_info['built_by']))
    click.echo("\nPlatform: {}".format(platform_info['platform']))
    click.echo("HwSKU: {}".format(platform_info['hwsku']))
    click.echo("ASIC: {}".format(platform_info['asic_type']))
    click.echo("ASIC Count: {}".format(platform_info['asic_count']))
    click.echo("Serial Number: {}".format(chassis_info['serial']))
    click.echo("Model Number: {}".format(chassis_info['model']))
    click.echo("Hardware Revision: {}".format(chassis_info['revision']))
    click.echo("Uptime: {}".format(sys_uptime.stdout.read().strip()))
    click.echo("Date: {}".format(sys_date.strftime("%a %d %b %Y %X")))
    click.echo("\nDocker images:")
    cmd = 'sudo docker images --format "table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.Size}}"'
    p = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE)
    click.echo(p.stdout.read())

#
# 'environment' command ("show environment")
#

@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def environment(verbose):
    """Show environmentals (voltages, fans, temps)"""
    cmd = "sudo sensors"
    run_command(cmd, display_cmd=verbose)


#
# 'users' command ("show users")
#

@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def users(verbose):
    """Show users"""
    cmd = "who"
    run_command(cmd, display_cmd=verbose)


#
# 'techsupport' command ("show techsupport")
#

@cli.command()
@click.option('--since', required=False, help="Collect logs and core files since given date")
@click.option('-g', '--global-timeout', required=False, type=int, help="Global timeout in minutes. WARN: Dump might be incomplete if enforced")
@click.option('-c', '--cmd-timeout', default=5, type=int, help="Individual command timeout in minutes. Default 5 mins")
@click.option('--verbose', is_flag=True, help="Enable verbose output")
@click.option('--allow-process-stop', is_flag=True, help="Dump additional data which may require system interruption")
@click.option('--silent', is_flag=True, help="Run techsupport in silent mode")
@click.option('--debug-dump', is_flag=True, help="Collect Debug Dump Output")
@click.option('--redirect-stderr', '-r', is_flag=True, help="Redirect an intermediate errors to STDERR")
def techsupport(since, global_timeout, cmd_timeout, verbose, allow_process_stop, silent, debug_dump, redirect_stderr):
    """Gather information for troubleshooting"""
    cmd = "sudo"

    if global_timeout:
        cmd += " timeout --kill-after={}s -s SIGTERM --foreground {}m".format(COMMAND_TIMEOUT, global_timeout)

    if silent:
        cmd += " generate_dump"
        click.echo("Techsupport is running with silent option. This command might take a long time.")
    else:
        cmd += " generate_dump -v"

    if allow_process_stop:
        cmd += " -a"

    if since:
        cmd += " -s '{}'".format(since)

    if debug_dump:
        cmd += " -d"

    cmd += " -t {}".format(cmd_timeout)
    if redirect_stderr:
        cmd += " -r"
    run_command(cmd, display_cmd=verbose)


#
# 'runningconfiguration' group ("show runningconfiguration")
#

@cli.group(cls=clicommon.AliasedGroup)
def runningconfiguration():
    """Show current running configuration information"""
    pass


# 'all' subcommand ("show runningconfiguration all")
@runningconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def all(verbose):
    """Show full running configuration"""
    cmd = ['sonic-cfggen', '-d', '--print-data']
    stdout, rc = get_cmd_output(cmd)
    if rc:
        click.echo("Failed to get cmd output '{}':rc {}".format(cmd, rc))
        raise click.Abort()

    try:
        output = json.loads(stdout)
    except JSONDecodeError as e:
        click.echo("Failed to load output '{}':{}".format(cmd, e))
        raise click.Abort()

    if not multi_asic.is_multi_asic():
        bgpraw_cmd = [constants.RVTYSH_COMMAND, '-c', 'show running-config']
        bgpraw, rc = get_cmd_output(bgpraw_cmd)
        if rc:
            bgpraw = ""
        output['bgpraw'] = bgpraw
    click.echo(json.dumps(output, indent=4))


# 'acl' subcommand ("show runningconfiguration acl")
@runningconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def acl(verbose):
    """Show acl running configuration"""
    cmd = "sonic-cfggen -d --var-json ACL_RULE"
    run_command(cmd, display_cmd=verbose)


# 'ports' subcommand ("show runningconfiguration ports <portname>")
@runningconfiguration.command()
@click.argument('portname', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ports(portname, verbose):
    """Show ports running configuration"""
    cmd = "sonic-cfggen -d --var-json PORT"

    if portname is not None:
        cmd += " {0} {1}".format("--key", portname)

    run_command(cmd, display_cmd=verbose)


# 'bgp' subcommand ("show runningconfiguration bgp")
@runningconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
@click.option('--namespace', '-n', 'namespace', required=False, default=None, type=str, show_default=False,
              help='Option needed for multi-asic only: provide namespace name',
              callback=multi_asic_util.multi_asic_namespace_validation_callback)
def bgp(namespace, verbose):
    """
    Show BGP running configuration
    Note:
        multi-asic can run 'show run bgp' and show from all asics, or 'show run bgp -n <ns>'
        single-asic only run 'show run bgp', '-n' is not available
    """

    if multi_asic.is_multi_asic():
        if namespace and namespace not in multi_asic.get_namespace_list():
            ctx = click.get_current_context()
            ctx.fail("invalid value for -n/--namespace option. provide namespace from list {}".format(multi_asic.get_namespace_list()))
    if not multi_asic.is_multi_asic() and namespace:
        ctx = click.get_current_context()
        ctx.fail("-n/--namespace is not available for single asic")

    output = ""
    cmd = "show running-config bgp"
    import utilities_common.bgp_util as bgp_util
    if multi_asic.is_multi_asic():
        if not namespace:
            ns_list = multi_asic.get_namespace_list()
            for ns in ns_list:
                output += "\n------------Showing running config bgp on {}------------\n".format(ns)
                output += bgp_util.run_bgp_show_command(cmd, ns)
        else:
            output += "\n------------Showing running config bgp on {}------------\n".format(namespace)
            output += bgp_util.run_bgp_show_command(cmd, namespace)
    else:
        output += bgp_util.run_bgp_show_command(cmd)
    print(output)


# 'interfaces' subcommand ("show runningconfiguration interfaces")
@runningconfiguration.command()
@click.argument('interfacename', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def interfaces(interfacename, verbose):
    """Show interfaces running configuration"""
    cmd = "sonic-cfggen -d --var-json INTERFACE"

    if interfacename is not None:
        cmd += " {0} {1}".format("--key", interfacename)

    run_command(cmd, display_cmd=verbose)


# 'ntp' subcommand ("show runningconfiguration ntp")
@runningconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ntp(verbose):
    """Show NTP running configuration"""
    ntp_servers = []
    ntp_dict = {}
    with open("/etc/ntp.conf") as ntp_file:
        data = ntp_file.readlines()
    for line in data:
        if line.startswith("server "):
            ntp_server = line.split(" ")[1]
            ntp_servers.append(ntp_server)
    ntp_dict['NTP Servers'] = ntp_servers
    print(tabulate(ntp_dict, headers=list(ntp_dict.keys()), tablefmt="simple", stralign='left', missingval=""))



# 'snmp' subcommand ("show runningconfiguration snmp")
@runningconfiguration.group("snmp", invoke_without_command=True)
@clicommon.pass_db
@click.pass_context
def snmp(ctx, db):
    """Show SNMP running configuration"""
    if ctx.invoked_subcommand is None:
       show_run_snmp(db.cfgdb)


# ("show runningconfiguration snmp community")
@snmp.command('community')
@click.option('--json', 'json_output', required=False, is_flag=True, type=click.BOOL,
              help="Display the output in JSON format")
@clicommon.pass_db
def community(db, json_output):
    """show SNMP running configuration community"""
    snmp_comm_header = ["Community String", "Community Type"]
    snmp_comm_body = []
    snmp_comm_keys = db.cfgdb.get_table('SNMP_COMMUNITY')
    snmp_comm_strings = snmp_comm_keys.keys()
    if json_output:
        click.echo(snmp_comm_keys)
    else:
        for line in snmp_comm_strings:
            comm_string = line
            comm_string_type = snmp_comm_keys[line]['TYPE']
            snmp_comm_body.append([comm_string, comm_string_type])
        click.echo(tabulate(natsorted(snmp_comm_body), snmp_comm_header))


# ("show runningconfiguration snmp contact")
@snmp.command('contact')
@click.option('--json', 'json_output', required=False, is_flag=True, type=click.BOOL,
              help="Display the output in JSON format")
@clicommon.pass_db
def contact(db, json_output):
    """show SNMP running configuration contact"""
    snmp = db.cfgdb.get_table('SNMP')
    snmp_header = ["Contact", "Contact Email"]
    snmp_body = []
    if json_output:
        try:
            if snmp['CONTACT']:
                click.echo(snmp['CONTACT'])
        except KeyError:
            snmp['CONTACT'] = {}
            click.echo(snmp['CONTACT'])
    else:
        try:
            if snmp['CONTACT']:
                snmp_contact = list(snmp['CONTACT'].keys())
                snmp_contact_email = [snmp['CONTACT'][snmp_contact[0]]]
                snmp_body.append([snmp_contact[0], snmp_contact_email[0]])
        except KeyError:
            snmp['CONTACT'] = ''
        click.echo(tabulate(snmp_body, snmp_header))


# ("show runningconfiguration snmp location")
@snmp.command('location')
@click.option('--json', 'json_output', required=False, is_flag=True, type=click.BOOL,
              help="Display the output in JSON format")
@clicommon.pass_db
def location(db, json_output):
    """show SNMP running configuration location"""
    snmp = db.cfgdb.get_table('SNMP')
    snmp_header = ["Location"]
    snmp_body = []
    if json_output:
        try:
            if snmp['LOCATION']:
                click.echo(snmp['LOCATION'])
        except KeyError:
            snmp['LOCATION'] = {}
            click.echo(snmp['LOCATION'])
    else:
        try:
            if snmp['LOCATION']:
                snmp_location = [snmp['LOCATION']['Location']]
                snmp_body.append(snmp_location)
        except KeyError:
            snmp['LOCATION'] = ''
        click.echo(tabulate(snmp_body, snmp_header))


# ("show runningconfiguration snmp user")
@snmp.command('user')
@click.option('--json', 'json_output', required=False, is_flag=True, type=click.BOOL,
              help="Display the output in JSON format")
@clicommon.pass_db
def users(db, json_output):
    """show SNMP running configuration user"""
    snmp_users = db.cfgdb.get_table('SNMP_USER')
    snmp_user_header = ['User', "Permission Type", "Type", "Auth Type", "Auth Password", "Encryption Type",
                        "Encryption Password"]
    snmp_user_body = []
    if json_output:
        click.echo(snmp_users)
    else:
        for snmp_user, snmp_user_value in snmp_users.items():
            snmp_user_permissions_type = snmp_users[snmp_user].get('SNMP_USER_PERMISSION', 'Null')
            snmp_user_auth_type = snmp_users[snmp_user].get('SNMP_USER_AUTH_TYPE', 'Null')
            snmp_user_auth_password = snmp_users[snmp_user].get('SNMP_USER_AUTH_PASSWORD', 'Null')
            snmp_user_encryption_type = snmp_users[snmp_user].get('SNMP_USER_ENCRYPTION_TYPE', 'Null')
            snmp_user_encryption_password = snmp_users[snmp_user].get('SNMP_USER_ENCRYPTION_PASSWORD', 'Null')
            snmp_user_type = snmp_users[snmp_user].get('SNMP_USER_TYPE', 'Null')
            snmp_user_body.append([snmp_user, snmp_user_permissions_type, snmp_user_type, snmp_user_auth_type,
                                   snmp_user_auth_password, snmp_user_encryption_type, snmp_user_encryption_password])
        click.echo(tabulate(natsorted(snmp_user_body), snmp_user_header))


# ("show runningconfiguration snmp")
@clicommon.pass_db
def show_run_snmp(db, ctx):
    snmp_contact_location_table = db.cfgdb.get_table('SNMP')
    snmp_comm_table = db.cfgdb.get_table('SNMP_COMMUNITY')
    snmp_users = db.cfgdb.get_table('SNMP_USER')
    snmp_location_header = ["Location"]
    snmp_location_body = []
    snmp_contact_header = ["SNMP_CONTACT", "SNMP_CONTACT_EMAIL"]
    snmp_contact_body = []
    snmp_comm_header = ["Community String", "Community Type"]
    snmp_comm_body = []
    snmp_user_header = ['User', "Permission Type", "Type", "Auth Type", "Auth Password", "Encryption Type",
                        "Encryption Password"]
    snmp_user_body = []
    try:
        if snmp_contact_location_table['LOCATION']:
            snmp_location = [snmp_contact_location_table['LOCATION']['Location']]
            snmp_location_body.append(snmp_location)
    except KeyError:
        snmp_contact_location_table['LOCATION'] = ''
    click.echo(tabulate(snmp_location_body, snmp_location_header))
    click.echo("\n")
    try:
        if snmp_contact_location_table['CONTACT']:
            snmp_contact = list(snmp_contact_location_table['CONTACT'].keys())
            snmp_contact_email = [snmp_contact_location_table['CONTACT'][snmp_contact[0]]]
            snmp_contact_body.append([snmp_contact[0], snmp_contact_email[0]])
    except KeyError:
        snmp_contact_location_table['CONTACT'] = ''
    click.echo(tabulate(snmp_contact_body, snmp_contact_header))
    click.echo("\n")
    snmp_comm_strings = snmp_comm_table.keys()
    for line in snmp_comm_strings:
        comm_string = line
        comm_string_type = snmp_comm_table[line]['TYPE']
        snmp_comm_body.append([comm_string, comm_string_type])
    click.echo(tabulate(natsorted(snmp_comm_body), snmp_comm_header))
    click.echo("\n")
    for snmp_user, snmp_user_value in snmp_users.items():
        snmp_user_permissions_type = snmp_users[snmp_user].get('SNMP_USER_PERMISSION', 'Null')
        snmp_user_auth_type = snmp_users[snmp_user].get('SNMP_USER_AUTH_TYPE', 'Null')
        snmp_user_auth_password = snmp_users[snmp_user].get('SNMP_USER_AUTH_PASSWORD', 'Null')
        snmp_user_encryption_type = snmp_users[snmp_user].get('SNMP_USER_ENCRYPTION_TYPE', 'Null')
        snmp_user_encryption_password = snmp_users[snmp_user].get('SNMP_USER_ENCRYPTION_PASSWORD', 'Null')
        snmp_user_type = snmp_users[snmp_user].get('SNMP_USER_TYPE', 'Null')
        snmp_user_body.append([snmp_user, snmp_user_permissions_type, snmp_user_type, snmp_user_auth_type,
                               snmp_user_auth_password, snmp_user_encryption_type, snmp_user_encryption_password])
    click.echo(tabulate(natsorted(snmp_user_body), snmp_user_header))


# 'syslog' subcommand ("show runningconfiguration syslog")
@runningconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def syslog(verbose):
    """Show Syslog running configuration"""

    header = ["Syslog Servers"]
    body = []

    re_syslog = re.compile(r'^\*\.\* action\(.*target=\"{1}(.+?)\"{1}.*\)')

    try:
        with open("/etc/rsyslog.conf") as syslog_file:
            data = syslog_file.readlines()
    except Exception as e:
        raise click.ClickException(str(e))

    for line in data:
        re_match = re_syslog.match(line)
        if re_match:
            body.append(["[{}]".format(re_match.group(1))])

    click.echo(tabulate(body, header, tablefmt="simple", stralign="left", missingval=""))


#
# 'startupconfiguration' group ("show startupconfiguration ...")
#

@cli.group(cls=clicommon.AliasedGroup)
def startupconfiguration():
    """Show startup configuration information"""
    pass


# 'bgp' subcommand  ("show startupconfiguration bgp")
@startupconfiguration.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def bgp(verbose):
    """Show BGP startup configuration"""
    cmd = "sudo docker ps | grep bgp | awk '{print$2}' | cut -d'-' -f3 | cut -d':' -f1"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, text=True)
    result = proc.stdout.read().rstrip()
    click.echo("Routing-Stack is: {}".format(result))
    if result == "quagga":
        run_command('sudo docker exec bgp cat /etc/quagga/bgpd.conf', display_cmd=verbose)
    elif result == "frr":
        run_command('sudo docker exec bgp cat /etc/frr/bgpd.conf', display_cmd=verbose)
    elif result == "gobgp":
        run_command('sudo docker exec bgp cat /etc/gpbgp/bgpd.conf', display_cmd=verbose)
    else:
        click.echo("Unidentified routing-stack")

#
# 'ntp' command ("show ntp")
#

@cli.command()
@click.pass_context
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ntp(ctx, verbose):
    """Show NTP information"""
    from pkg_resources import parse_version
    ntpstat_cmd = "ntpstat"
    ntpcmd = "ntpq -p -n"
    if is_mgmt_vrf_enabled(ctx) is True:
        #ManagementVRF is enabled. Call ntpq using "ip vrf exec" or cgexec based on linux version
        os_info =  os.uname()
        release = os_info[2].split('-')
        if parse_version(release[0]) > parse_version("4.9.0"):
            ntpstat_cmd = "sudo ip vrf exec mgmt ntpstat"
            ntpcmd = "sudo ip vrf exec mgmt ntpq -p -n"
        else:
            ntpstat_cmd = "sudo cgexec -g l3mdev:mgmt ntpstat"
            ntpcmd = "sudo cgexec -g l3mdev:mgmt ntpq -p -n"

    run_command(ntpstat_cmd, display_cmd=verbose)
    run_command(ntpcmd, display_cmd=verbose)

#
# 'uptime' command ("show uptime")
#

@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def uptime(verbose):
    """Show system uptime"""
    cmd = "uptime -p"
    run_command(cmd, display_cmd=verbose)

@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def clock(verbose):
    """Show date and time"""
    cmd ="date"
    run_command(cmd, display_cmd=verbose)

@cli.command('system-memory')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def system_memory(verbose):
    """Show memory information"""
    cmd = "free -m"
    run_command(cmd, display_cmd=verbose)


@cli.command('services')
def services():
    """Show all daemon services"""
    cmd = "sudo docker ps --format '{{.Names}}'"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, text=True)
    while True:
        line = proc.stdout.readline()
        if line != '':
                print(line.rstrip()+'\t'+"docker")
                print("---------------------------")
                cmd = "sudo docker exec {} ps aux | sed '$d'".format(line.rstrip())
                proc1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, text=True)
                print(proc1.stdout.read())
        else:
                break

@cli.command()
@clicommon.pass_db
def aaa(db):
    """Show AAA configuration"""
    config_db = db.cfgdb
    data = config_db.get_table('AAA')
    output = ''

    aaa = {
        'authentication': {
            'login': 'local (default)',
            'failthrough': 'False (default)'
        },
        'authorization': {
            'login': 'local (default)'
        },
        'accounting': {
            'login': 'disable (default)'
        }
    }
    if 'authentication' in data:
        aaa['authentication'].update(data['authentication'])
    if 'authorization' in data:
        aaa['authorization'].update(data['authorization'])
    if 'accounting' in data:
        aaa['accounting'].update(data['accounting'])
    for row in aaa:
        entry = aaa[row]
        for key in entry:
            output += ('AAA %s %s %s\n' % (row, key, str(entry[key])))
    click.echo(output)


@cli.command()
def tacacs():
    """Show TACACS+ configuration"""
    config_db = ConfigDBConnector()
    config_db.connect()
    output = ''
    data = config_db.get_table('TACPLUS')

    tacplus = {
        'global': {
            'auth_type': 'pap (default)',
            'timeout': '5 (default)',
            'passkey': '<EMPTY_STRING> (default)'
        }
    }
    if 'global' in data:
        tacplus['global'].update(data['global'])
    for key in tacplus['global']:
        output += ('TACPLUS global %s %s\n' % (str(key), str(tacplus['global'][key])))

    data = config_db.get_table('TACPLUS_SERVER')
    if data != {}:
        for row in data:
            entry = data[row]
            output += ('\nTACPLUS_SERVER address %s\n' % row)
            for key in entry:
                output += ('               %s %s\n' % (key, str(entry[key])))
    click.echo(output)

@cli.command()
@clicommon.pass_db
def radius(db):
    """Show RADIUS configuration"""
    output = ''
    config_db = db.cfgdb
    data = config_db.get_table('RADIUS')

    radius = {
        'global': {
            'auth_type': 'pap (default)',
            'retransmit': '3 (default)',
            'timeout': '5 (default)',
            'passkey': '<EMPTY_STRING> (default)'
        }
    }
    if 'global' in data:
        radius['global'].update(data['global'])
    for key in radius['global']:
        output += ('RADIUS global %s %s\n' % (str(key), str(radius['global'][key])))

    data = config_db.get_table('RADIUS_SERVER')
    if data != {}:
        for row in data:
            entry = data[row]
            output += ('\nRADIUS_SERVER address %s\n' % row)
            for key in entry:
                output += ('               %s %s\n' % (key, str(entry[key])))

    counters_db = SonicV2Connector(host='127.0.0.1')
    counters_db.connect(counters_db.COUNTERS_DB, retry_on=False)

    if radius['global'].get('statistics', False) and (data != {}):
        for row in data:
            exists = counters_db.exists(counters_db.COUNTERS_DB,
                                     'RADIUS_SERVER_STATS:{}'.format(row))
            if not exists:
                continue

            counter_entry = counters_db.get_all(counters_db.COUNTERS_DB,
                    'RADIUS_SERVER_STATS:{}'.format(row))
            output += ('\nStatistics for RADIUS_SERVER address %s\n' % row)
            for key in counter_entry:
                if counter_entry[key] != "0":
                    output += ('               %s %s\n' % (key, str(counter_entry[key])))
    try:
        counters_db.close(counters_db.COUNTERS_DB)
    except Exception as e:
        pass

    click.echo(output)

#
# 'mirror_session' command  ("show mirror_session ...")
#
@cli.command('mirror_session')
@click.argument('session_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def mirror_session(session_name, verbose):
    """Show existing everflow sessions"""
    cmd = "acl-loader show session"

    if session_name is not None:
        cmd += " {}".format(session_name)

    run_command(cmd, display_cmd=verbose)


#
# 'policer' command  ("show policer ...")
#
@cli.command()
@click.argument('policer_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def policer(policer_name, verbose):
    """Show existing policers"""
    cmd = "acl-loader show policer"

    if policer_name is not None:
        cmd += " {}".format(policer_name)

    run_command(cmd, display_cmd=verbose)


#
# 'ecn' command ("show ecn")
#
@cli.command('ecn')
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ecn(verbose):
    """Show ECN configuration"""
    cmd = "ecnconfig -l"
    run_command(cmd, display_cmd=verbose)


#
# 'boot' command ("show boot")
#
@cli.command('boot')
def boot():
    """Show boot configuration"""
    cmd = "sudo sonic-installer list"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, text=True)
    click.echo(proc.stdout.read())


#
# 'mmu' command ("show mmu")
#
@cli.command('mmu')
def mmu():
    """Show mmu configuration"""
    cmd = "mmuconfig -l"
    run_command(cmd)

#
# 'buffer' command ("show buffer")
#
@cli.group(cls=clicommon.AliasedGroup)
def buffer():
    """Show buffer information"""
    pass

#
# 'configuration' command ("show buffer command")
#
@buffer.command()
def configuration():
    """show buffer configuration"""
    cmd = "mmuconfig -l"
    run_command(cmd)

#
# 'information' command ("show buffer state")
#
@buffer.command()
def information():
    """show buffer information"""
    cmd = "buffershow -l"
    run_command(cmd)


#
# 'line' command ("show line")
#
@cli.command('line')
@click.option('--brief', '-b', metavar='<brief_mode>', required=False, is_flag=True)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def line(brief, verbose):
    """Show all console lines and their info include available ttyUSB devices unless specified brief mode"""
    cmd = "consutil show" + (" -b" if brief else "")
    run_command(cmd, display_cmd=verbose)
    return


#
# 'ztp status' command ("show ztp status")
#
@cli.command()
@click.argument('status', required=False, type=click.Choice(["status"]))
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def ztp(status, verbose):
    """Show Zero Touch Provisioning status"""
    if os.path.isfile('/usr/bin/ztp') is False:
        exit("ZTP feature unavailable in this image version")

    cmd = "ztp status"
    if verbose:
       cmd = cmd + " --verbose"
    run_command(cmd, display_cmd=verbose)


#
# 'bfd' group ("show bfd ...")
#
@cli.group(cls=clicommon.AliasedGroup)
def bfd():
    """Show details of the bfd sessions"""
    pass

# 'summary' subcommand ("show bfd summary")
@bfd.command()
@clicommon.pass_db
def summary(db):
    """Show bfd session information"""
    bfd_headers = ["Peer Addr", "Interface", "Vrf", "State", "Type", "Local Addr",
                "TX Interval", "RX Interval", "Multiplier", "Multihop", "Local Discriminator"]

    bfd_keys = db.db.keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*")

    click.echo("Total number of BFD sessions: {}".format(0 if bfd_keys is None else len(bfd_keys)))

    bfd_body = []
    if bfd_keys is not None:
        for key in bfd_keys:
            key_values = key.split('|')
            values = db.db.get_all(db.db.STATE_DB, key)
            if "local_discriminator" not in values.keys():
                values["local_discriminator"] = "NA"            
            bfd_body.append([key_values[3], key_values[2], key_values[1], values["state"], values["type"], values["local_addr"],
                                values["tx_interval"], values["rx_interval"], values["multiplier"], values["multihop"], values["local_discriminator"]])

    click.echo(tabulate(bfd_body, bfd_headers))


# 'peer' subcommand ("show bfd peer ...")
@bfd.command()
@clicommon.pass_db
@click.argument('peer_ip', required=True)
def peer(db, peer_ip):
    """Show bfd session information for BFD peer"""
    bfd_headers = ["Peer Addr", "Interface", "Vrf", "State", "Type", "Local Addr",
                "TX Interval", "RX Interval", "Multiplier", "Multihop", "Local Discriminator"]

    bfd_keys = db.db.keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*|{}".format(peer_ip))
    delimiter = db.db.get_db_separator(db.db.STATE_DB)

    if bfd_keys is None or len(bfd_keys) == 0:
        click.echo("No BFD sessions found for peer IP {}".format(peer_ip))
        return

    click.echo("Total number of BFD sessions for peer IP {}: {}".format(peer_ip, len(bfd_keys)))

    bfd_body = []
    if bfd_keys is not None:
        for key in bfd_keys:
            key_values = key.split(delimiter)
            values = db.db.get_all(db.db.STATE_DB, key)
            if "local_discriminator" not in values.keys():
                values["local_discriminator"] = "NA"            
            bfd_body.append([key_values[3], key_values[2], key_values[1], values.get("state"), values.get("type"), values.get("local_addr"),
                                values.get("tx_interval"), values.get("rx_interval"), values.get("multiplier"), values.get("multihop"), values.get("local_discriminator")])

    click.echo(tabulate(bfd_body, bfd_headers))


# 'suppress-fib-pending' subcommand ("show suppress-fib-pending")
@cli.command('suppress-fib-pending')
@clicommon.pass_db
def suppress_pending_fib(db):
    """ Show the status of suppress pending FIB feature """

    field_values = db.cfgdb.get_entry('DEVICE_METADATA', 'localhost')
    state = field_values.get('suppress-fib-pending', 'disabled').title()
    click.echo(state)


# Load plugins and register them
helper = util_base.UtilHelper()
helper.load_and_register_plugins(plugins, cli)

if __name__ == '__main__':
    cli()
