import click
import json
from flow_counter_util.route import exit_if_route_flow_counter_not_support
from swsscommon.swsscommon import ConfigDBConnector
from tabulate import tabulate

BUFFER_POOL_WATERMARK = "BUFFER_POOL_WATERMARK"
PORT_BUFFER_DROP = "PORT_BUFFER_DROP"
PG_DROP = "PG_DROP"
ACL = "ACL"
DISABLE = "disable"
ENABLE = "enable"
DEFLT_60_SEC= "default (60000)"
DEFLT_10_SEC= "default (10000)"
DEFLT_1_SEC = "default (1000)"

@click.group()
def cli():
    """ SONiC Static Counter Poll configurations """

# Queue counter commands
@cli.group()
def queue():
    """ Queue counter commands """

@queue.command()
@click.argument('poll_interval', type=click.IntRange(100, 30000))
def interval(poll_interval):
    """ Set queue counter query interval """
    configdb = ConfigDBConnector()
    configdb.connect()
    queue_info = {}
    if poll_interval is not None:
        queue_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE", queue_info)

@queue.command()
def enable():
    """ Enable queue counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    queue_info = {}
    queue_info['FLEX_COUNTER_STATUS'] = 'enable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE", queue_info)

@queue.command()
def disable():
    """ Disable queue counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    queue_info = {}
    queue_info['FLEX_COUNTER_STATUS'] = 'disable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE", queue_info)

# Port counter commands
@cli.group()
def port():
    """ Port counter commands """

@port.command()
@click.argument('poll_interval', type=click.IntRange(100, 30000))
def interval(poll_interval):
    """ Set port counter query interval """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    if poll_interval is not None:
        port_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PORT", port_info)

@port.command()
def enable():
    """ Enable port counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = 'enable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PORT", port_info)

@port.command()
def disable():
    """ Disable port counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = 'disable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PORT", port_info)

# Port buffer drop counter commands
@cli.group()
def port_buffer_drop():
    """ Port buffer drop  counter commands """

@port_buffer_drop.command()
@click.argument('poll_interval', type=click.IntRange(30000, 300000))
def interval(poll_interval):
    """
    Set port_buffer_drop counter query interval
    This counter group causes high CPU usage when polled,
    hence the allowed interval is between 30s and 300s.
    This is a short term solution and
    should be changed once the performance is enhanced
    """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    if poll_interval:
        port_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", PORT_BUFFER_DROP, port_info)

@port_buffer_drop.command()
def enable():
    """ Enable port counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = ENABLE
    configdb.mod_entry("FLEX_COUNTER_TABLE", PORT_BUFFER_DROP, port_info)

@port_buffer_drop.command()
def disable():
    """ Disable port counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = DISABLE
    configdb.mod_entry("FLEX_COUNTER_TABLE", PORT_BUFFER_DROP, port_info)

# Ingress PG drop packet stat
@cli.group()
@click.pass_context
def pg_drop(ctx):
    """  Ingress PG drop counter commands """
    ctx.obj = ConfigDBConnector()
    ctx.obj.connect()

@pg_drop.command()
@click.argument('poll_interval', type=click.IntRange(1000, 30000))
@click.pass_context
def interval(ctx, poll_interval):
    """
    Set pg_drop packets counter query interval
    interval is between 1s and 30s.
    """

    port_info = {}
    port_info['POLL_INTERVAL'] = poll_interval
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", PG_DROP, port_info)

@pg_drop.command()
@click.pass_context
def enable(ctx):
    """ Enable pg_drop counter query """

    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = ENABLE
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", PG_DROP, port_info)

@pg_drop.command()
@click.pass_context
def disable(ctx):
    """ Disable pg_drop counter query """

    port_info = {}
    port_info['FLEX_COUNTER_STATUS'] = DISABLE
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", PG_DROP, port_info)

# RIF counter commands
@cli.group()
def rif():
    """ RIF counter commands """

@rif.command()
@click.argument('poll_interval')
def interval(poll_interval):
    """ Set rif counter query interval """
    configdb = ConfigDBConnector()
    configdb.connect()
    rif_info = {}
    if poll_interval is not None:
        rif_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", "RIF", rif_info)

@rif.command()
def enable():
    """ Enable rif counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    rif_info = {}
    rif_info['FLEX_COUNTER_STATUS'] = 'enable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "RIF", rif_info)

@rif.command()
def disable():
    """ Disable rif counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    rif_info = {}
    rif_info['FLEX_COUNTER_STATUS'] = 'disable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "RIF", rif_info)

# Watermark counter commands
@cli.group()
def watermark():
    """ Watermark counter commands """

@watermark.command()
@click.argument('poll_interval', type=click.IntRange(1000, 60000))
def interval(poll_interval):
    """ Set watermark counter query interval for both queue and PG watermarks """
    configdb = ConfigDBConnector()
    configdb.connect()
    queue_wm_info = {}
    pg_wm_info = {}
    buffer_pool_wm_info = {}
    if poll_interval is not None:
        queue_wm_info['POLL_INTERVAL'] = poll_interval
        pg_wm_info['POLL_INTERVAL'] = poll_interval
        buffer_pool_wm_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE_WATERMARK", queue_wm_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PG_WATERMARK", pg_wm_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", BUFFER_POOL_WATERMARK, buffer_pool_wm_info)

@watermark.command()
def enable():
    """ Enable watermark counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'enable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE_WATERMARK", fc_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PG_WATERMARK", fc_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", BUFFER_POOL_WATERMARK, fc_info)

@watermark.command()
def disable():
    """ Disable watermark counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'disable'
    configdb.mod_entry("FLEX_COUNTER_TABLE", "QUEUE_WATERMARK", fc_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", "PG_WATERMARK", fc_info)
    configdb.mod_entry("FLEX_COUNTER_TABLE", BUFFER_POOL_WATERMARK, fc_info)

# ACL counter commands
@cli.group()
@click.pass_context
def acl(ctx):
    """  ACL counter commands """
    ctx.obj = ConfigDBConnector()
    ctx.obj.connect()

@acl.command()
@click.argument('poll_interval', type=click.IntRange(1000, 30000))
@click.pass_context
def interval(ctx, poll_interval):
    """
    Set ACL counters query interval
    interval is between 1s and 30s.
    """

    fc_group_cfg = {}
    fc_group_cfg['POLL_INTERVAL'] = poll_interval
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", ACL, fc_group_cfg)

@acl.command()
@click.pass_context
def enable(ctx):
    """ Enable ACL counter query """

    fc_group_cfg = {}
    fc_group_cfg['FLEX_COUNTER_STATUS'] = ENABLE
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", ACL, fc_group_cfg)

@acl.command()
@click.pass_context
def disable(ctx):
    """ Disable ACL counter query """

    fc_group_cfg = {}
    fc_group_cfg['FLEX_COUNTER_STATUS'] = DISABLE
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", ACL, fc_group_cfg)

# Tunnel counter commands
@cli.group()
def tunnel():
    """ Tunnel counter commands """

@tunnel.command()
@click.argument('poll_interval', type=click.IntRange(100, 30000))
def interval(poll_interval):
    """ Set tunnel counter query interval """
    configdb = ConfigDBConnector()
    configdb.connect()
    tunnel_info = {}
    tunnel_info['POLL_INTERVAL'] = poll_interval
    configdb.mod_entry("FLEX_COUNTER_TABLE", "TUNNEL", tunnel_info)

@tunnel.command()
def enable():
    """ Enable tunnel counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    tunnel_info = {}
    tunnel_info['FLEX_COUNTER_STATUS'] = ENABLE
    configdb.mod_entry("FLEX_COUNTER_TABLE", "TUNNEL", tunnel_info)

@tunnel.command()
def disable():
    """ Disable tunnel counter query """
    configdb = ConfigDBConnector()
    configdb.connect()
    tunnel_info = {}
    tunnel_info['FLEX_COUNTER_STATUS'] = DISABLE
    configdb.mod_entry("FLEX_COUNTER_TABLE", "TUNNEL", tunnel_info)

# Trap flow counter commands
@cli.group()
@click.pass_context
def flowcnt_trap(ctx):
    """ Trap flow counter commands """
    ctx.obj = ConfigDBConnector()
    ctx.obj.connect()

@flowcnt_trap.command()
@click.argument('poll_interval', type=click.IntRange(1000, 30000))
@click.pass_context
def interval(ctx, poll_interval):
    """ Set trap flow counter query interval """
    fc_info = {}
    fc_info['POLL_INTERVAL'] = poll_interval
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_TRAP", fc_info)

@flowcnt_trap.command()
@click.pass_context
def enable(ctx):
    """ Enable trap flow counter query """
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'enable'
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_TRAP", fc_info)

@flowcnt_trap.command()
@click.pass_context
def disable(ctx):
    """ Disable trap flow counter query """
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'disable'
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_TRAP", fc_info)

# Route flow counter commands
@cli.group()
@click.pass_context
def flowcnt_route(ctx):
    """ Route flow counter commands """
    exit_if_route_flow_counter_not_support()
    ctx.obj = ConfigDBConnector()
    ctx.obj.connect()

@flowcnt_route.command()
@click.argument('poll_interval', type=click.IntRange(1000, 30000))
@click.pass_context
def interval(ctx, poll_interval):
    """ Set route flow counter query interval """
    fc_info = {}
    fc_info['POLL_INTERVAL'] = poll_interval
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_ROUTE", fc_info)

@flowcnt_route.command()
@click.pass_context
def enable(ctx):
    """ Enable route flow counter query """
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'enable'
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_ROUTE", fc_info)

@flowcnt_route.command()
@click.pass_context
def disable(ctx):
    """ Disable route flow counter query """
    fc_info = {}
    fc_info['FLEX_COUNTER_STATUS'] = 'disable'
    ctx.obj.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_ROUTE", fc_info)

@cli.command()
def show():
    """ Show the counter configuration """
    configdb = ConfigDBConnector()
    configdb.connect()
    queue_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'QUEUE')
    port_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'PORT')
    port_drop_info = configdb.get_entry('FLEX_COUNTER_TABLE', PORT_BUFFER_DROP)
    rif_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'RIF')
    queue_wm_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'QUEUE_WATERMARK')
    pg_wm_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'PG_WATERMARK')
    pg_drop_info = configdb.get_entry('FLEX_COUNTER_TABLE', PG_DROP)
    buffer_pool_wm_info = configdb.get_entry('FLEX_COUNTER_TABLE', BUFFER_POOL_WATERMARK)
    acl_info = configdb.get_entry('FLEX_COUNTER_TABLE', ACL)
    tunnel_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'TUNNEL')
    trap_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'FLOW_CNT_TRAP')
    route_info = configdb.get_entry('FLEX_COUNTER_TABLE', 'FLOW_CNT_ROUTE')

    header = ("Type", "Interval (in ms)", "Status")
    data = []
    if queue_info:
        data.append(["QUEUE_STAT", queue_info.get("POLL_INTERVAL", DEFLT_10_SEC), queue_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if port_info:
        data.append(["PORT_STAT", port_info.get("POLL_INTERVAL", DEFLT_1_SEC), port_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if port_drop_info:
        data.append([PORT_BUFFER_DROP, port_drop_info.get("POLL_INTERVAL", DEFLT_60_SEC), port_drop_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if rif_info:
        data.append(["RIF_STAT", rif_info.get("POLL_INTERVAL", DEFLT_1_SEC), rif_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if queue_wm_info:
        data.append(["QUEUE_WATERMARK_STAT", queue_wm_info.get("POLL_INTERVAL", DEFLT_60_SEC), queue_wm_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if pg_wm_info:
        data.append(["PG_WATERMARK_STAT", pg_wm_info.get("POLL_INTERVAL", DEFLT_60_SEC), pg_wm_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if pg_drop_info:
        data.append(['PG_DROP_STAT', pg_drop_info.get("POLL_INTERVAL", DEFLT_10_SEC), pg_drop_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if buffer_pool_wm_info:
        data.append(["BUFFER_POOL_WATERMARK_STAT", buffer_pool_wm_info.get("POLL_INTERVAL", DEFLT_60_SEC), buffer_pool_wm_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if acl_info:
        data.append([ACL, acl_info.get("POLL_INTERVAL", DEFLT_10_SEC), acl_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if tunnel_info:
        data.append(["TUNNEL_STAT", tunnel_info.get("POLL_INTERVAL", DEFLT_10_SEC), tunnel_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if trap_info:
        data.append(["FLOW_CNT_TRAP_STAT", trap_info.get("POLL_INTERVAL", DEFLT_10_SEC), trap_info.get("FLEX_COUNTER_STATUS", DISABLE)])
    if route_info:
        data.append(["FLOW_CNT_ROUTE_STAT", route_info.get("POLL_INTERVAL", DEFLT_10_SEC),
                     route_info.get("FLEX_COUNTER_STATUS", DISABLE)])

    click.echo(tabulate(data, headers=header, tablefmt="simple", missingval=""))

def _update_config_db_flex_counter_table(status, filename):
    """ Update counter configuration in config_db file """
    with open(filename) as config_db_file:
        config_db = json.load(config_db_file)

    write_config_db = False
    if "FLEX_COUNTER_TABLE" in config_db:
        if status != "delay":
            for counter, counter_config in config_db["FLEX_COUNTER_TABLE"].items():
                if "FLEX_COUNTER_STATUS" in counter_config and \
                    counter_config["FLEX_COUNTER_STATUS"] is not status:
                    counter_config["FLEX_COUNTER_STATUS"] = status
                    write_config_db = True

        elif status == "delay":
            write_config_db = True
            for key in config_db["FLEX_COUNTER_TABLE"].keys():
                config_db["FLEX_COUNTER_TABLE"][key].update({"FLEX_COUNTER_DELAY_STATUS":"true"})

    if write_config_db:
        with open(filename, 'w') as config_db_file:
            json.dump(config_db, config_db_file, indent=4)

# Working on Config DB
@cli.group()
def config_db():
    """ Config DB counter commands """

@config_db.command()
@click.argument("filename", default="/etc/sonic/config_db.json", type=click.Path(exists=True))
def enable(filename):
    """ Enable counter configuration in config_db file """
    _update_config_db_flex_counter_table("enable", filename)

@config_db.command()
@click.argument("filename", default="/etc/sonic/config_db.json", type=click.Path(exists=True))
def disable(filename):
    """ Disable counter configuration in config_db file """
    _update_config_db_flex_counter_table("disable", filename)

@config_db.command()
@click.argument("filename", default="/etc/sonic/config_db.json", type=click.Path(exists=True))
def delay(filename):
    """ Delay counters in config_db file """
    _update_config_db_flex_counter_table("delay", filename)
