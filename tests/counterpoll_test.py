import click
import json
import os
import pytest
import sys
from click.testing import CliRunner
from shutil import copyfile
from utilities_common.db import Db

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, test_path)
sys.path.insert(0, modules_path)

from .mock_tables import dbconnector

import counterpoll.main as counterpoll

expected_counterpoll_show = """Type                  Interval (in ms)    Status
--------------------  ------------------  --------
QUEUE_STAT            10000               enable
PORT_STAT             1000                enable
PORT_BUFFER_DROP      60000               enable
QUEUE_WATERMARK_STAT  default (60000)     enable
PG_WATERMARK_STAT     default (60000)     enable
PG_DROP_STAT          10000               enable
ACL                   5000                enable
TUNNEL_STAT           3000                enable
FLOW_CNT_TRAP_STAT    10000               enable
FLOW_CNT_ROUTE_STAT   10000               enable
"""

class TestCounterpoll(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["PATH"] += os.pathsep + scripts_path
        os.environ["UTILITIES_UNIT_TESTING"] = "1"

    def test_show(self):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["show"], [])
        print(result.output)
        assert result.output == expected_counterpoll_show

    def test_port_buffer_drop_interval(self):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["port-buffer-drop"].commands["interval"], ["30000"])
        print(result.output)
        assert result.exit_code == 0

    def test_port_buffer_drop_interval_too_short(self):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["port-buffer-drop"].commands["interval"], ["1000"])
        print(result.output)
        expected = "Invalid value for \"POLL_INTERVAL\": 1000 is not in the valid range of 30000 to 300000."
        assert result.exit_code == 2
        assert expected in result.output

    def test_pg_drop_interval_too_long(self):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["pg-drop"].commands["interval"], ["50000"])
        print(result.output)
        expected = "Invalid value for \"POLL_INTERVAL\": 50000 is not in the valid range of 1000 to 30000."
        assert result.exit_code == 2
        assert expected in result.output

    @pytest.mark.parametrize("interval", [100, 50000])
    def test_acl_interval_range(self, interval):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["acl"].commands["interval"], [str(interval)])
        print(result.output)
        expected = "Invalid value for \"POLL_INTERVAL\": {} is not in the valid range of 1000 to 30000.".format(interval)
        assert result.exit_code == 2
        assert expected in result.output

    @pytest.fixture(scope='class')
    def _get_config_db_file(self):
        sample_config_db_file = os.path.join(test_path, "counterpoll_input", "config_db.json")
        config_db_file = os.path.join('/', "tmp", "config_db.json")
        copyfile(sample_config_db_file, config_db_file)

        yield config_db_file

        os.remove(config_db_file)

    @pytest.mark.parametrize("status", ["disable", "enable"])
    def test_update_counter_config_db_status(self, status, _get_config_db_file):
        runner = CliRunner()
        result = runner.invoke(counterpoll.cli.commands["config-db"].commands[status], [_get_config_db_file])

        with open(_get_config_db_file) as json_file:
            config_db = json.load(json_file)

        if "FLEX_COUNTER_TABLE" in config_db:
            for counter, counter_config in config_db["FLEX_COUNTER_TABLE"].items():
                assert counter_config["FLEX_COUNTER_STATUS"] == status

    @pytest.mark.parametrize("status", ["disable", "enable"])
    def test_update_pg_drop_status(self, status):
        runner = CliRunner()
        db = Db()

        result = runner.invoke(counterpoll.cli.commands["pg-drop"].commands[status], [], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert status == table["PG_DROP"]["FLEX_COUNTER_STATUS"]

    def test_update_pg_drop_interval(self):
        runner = CliRunner()
        db = Db()
        test_interval = "20000"

        result = runner.invoke(counterpoll.cli.commands["pg-drop"].commands["interval"], [test_interval], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert test_interval == table["PG_DROP"]["POLL_INTERVAL"]

    @pytest.mark.parametrize("status", ["disable", "enable"])
    def test_update_acl_status(self, status):
        runner = CliRunner()
        db = Db()

        result = runner.invoke(counterpoll.cli.commands["acl"].commands[status], [], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table("FLEX_COUNTER_TABLE")
        assert status == table["ACL"]["FLEX_COUNTER_STATUS"]

    def test_update_acl_interval(self):
        runner = CliRunner()
        db = Db()
        test_interval = "20000"

        result = runner.invoke(counterpoll.cli.commands["acl"].commands["interval"], [test_interval], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table("FLEX_COUNTER_TABLE")
        assert test_interval == table["ACL"]["POLL_INTERVAL"]

    @pytest.mark.parametrize("status", ["disable", "enable"])
    def test_update_trap_counter_status(self, status):
        runner = CliRunner()
        db = Db()

        result = runner.invoke(counterpoll.cli.commands["flowcnt-trap"].commands[status], [], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert status == table["FLOW_CNT_TRAP"]["FLEX_COUNTER_STATUS"]

    @pytest.mark.parametrize("status", ["disable", "enable"])
    def test_update_route_flow_counter_status(self, status):
        runner = CliRunner()
        db = Db()

        result = runner.invoke(counterpoll.cli.commands["flowcnt-route"].commands[status], [], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert status == table["FLOW_CNT_ROUTE"]["FLEX_COUNTER_STATUS"]

    def test_update_trap_counter_interval(self):
        runner = CliRunner()
        db = Db()
        test_interval = "20000"

        result = runner.invoke(counterpoll.cli.commands["flowcnt-trap"].commands["interval"], [test_interval], obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert test_interval == table["FLOW_CNT_TRAP"]["POLL_INTERVAL"]

        test_interval = "500"
        result = runner.invoke(counterpoll.cli.commands["flowcnt-trap"].commands["interval"], [test_interval], obj=db.cfgdb)
        expected = "Invalid value for \"POLL_INTERVAL\": 500 is not in the valid range of 1000 to 30000."
        assert result.exit_code == 2
        assert expected in result.output

        test_interval = "40000"
        result = runner.invoke(counterpoll.cli.commands["flowcnt-trap"].commands["interval"], [test_interval], obj=db.cfgdb)
        expected = "Invalid value for \"POLL_INTERVAL\": 40000 is not in the valid range of 1000 to 30000."
        assert result.exit_code == 2
        assert expected in result.output

    def test_update_route_counter_interval(self):
        runner = CliRunner()
        db = Db()
        test_interval = "20000"

        result = runner.invoke(counterpoll.cli.commands["flowcnt-route"].commands["interval"], [test_interval],
                               obj=db.cfgdb)
        print(result.exit_code, result.output)
        assert result.exit_code == 0

        table = db.cfgdb.get_table('FLEX_COUNTER_TABLE')
        assert test_interval == table["FLOW_CNT_ROUTE"]["POLL_INTERVAL"]

        test_interval = "500"
        result = runner.invoke(counterpoll.cli.commands["flowcnt-route"].commands["interval"], [test_interval],
                               obj=db.cfgdb)
        expected = "Invalid value for \"POLL_INTERVAL\": 500 is not in the valid range of 1000 to 30000."
        assert result.exit_code == 2
        assert expected in result.output

        test_interval = "40000"
        result = runner.invoke(counterpoll.cli.commands["flowcnt-route"].commands["interval"], [test_interval],
                               obj=db.cfgdb)

        expected = "Invalid value for \"POLL_INTERVAL\": 40000 is not in the valid range of 1000 to 30000."
        assert result.exit_code == 2
        assert expected in result.output


    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
