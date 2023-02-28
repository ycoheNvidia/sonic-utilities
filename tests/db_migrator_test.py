import os
import pytest
import sys

from deepdiff import DeepDiff

from swsscommon.swsscommon import SonicV2Connector
from sonic_py_common import device_info

from .mock_tables import dbconnector

import config.main as config
from utilities_common.db import Db

test_path = os.path.dirname(os.path.abspath(__file__))
mock_db_path = os.path.join(test_path, "db_migrator_input")
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, test_path)
sys.path.insert(0, modules_path)
sys.path.insert(0, scripts_path)

os.environ["PATH"] += os.pathsep + scripts_path

def get_sonic_version_info_mlnx():
    return {'asic_type': 'mellanox'}


def advance_version_for_expected_database(migrated_db, expected_db, last_interested_version):
    # In case there are new db versions greater than the latest one that mellanox buffer migrator is interested,
    # we just advance the database version in the expected database to make the test pass
    expected_dbversion = expected_db.get_entry('VERSIONS', 'DATABASE')
    dbmgtr_dbversion = migrated_db.get_entry('VERSIONS', 'DATABASE')
    if expected_dbversion and dbmgtr_dbversion:
        if expected_dbversion['VERSION'] == last_interested_version and dbmgtr_dbversion['VERSION'] > expected_dbversion['VERSION']:
            expected_dbversion['VERSION'] = dbmgtr_dbversion['VERSION']
            expected_db.set_entry('VERSIONS', 'DATABASE', expected_dbversion)


class TestMellanoxBufferMigrator(object):
    @classmethod
    def setup_class(cls):
        cls.config_db_tables_to_verify = ['BUFFER_POOL', 'BUFFER_PROFILE', 'BUFFER_PG', 'DEFAULT_LOSSLESS_BUFFER_PARAMETER', 'LOSSLESS_TRAFFIC_PATTERN', 'VERSIONS', 'DEVICE_METADATA']
        cls.appl_db_tables_to_verify = ['BUFFER_POOL_TABLE:*', 'BUFFER_PROFILE_TABLE:*', 'BUFFER_PG_TABLE:*', 'BUFFER_QUEUE:*', 'BUFFER_PORT_INGRESS_PROFILE_LIST:*', 'BUFFER_PORT_EGRESS_PROFILE_LIST:*']
        cls.warm_reboot_from_version = 'version_1_0_6'
        cls.warm_reboot_to_version = 'version_3_0_3'

        cls.version_list = ['version_1_0_1', 'version_1_0_2', 'version_1_0_3', 'version_1_0_4', 'version_1_0_5', 'version_1_0_6', 'version_3_0_0', 'version_3_0_3']
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"

    def make_db_name_by_sku_topo_version(self, sku, topo, version):
        return sku + '-' + topo + '-' + version

    def mock_dedicated_config_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'config_db', filename)
        dbconnector.dedicated_dbs['CONFIG_DB'] = jsonfile
        db = Db()
        return db

    def mock_dedicated_state_db(self):
        dbconnector.dedicated_dbs['STATE_DB'] = os.path.join(mock_db_path, 'state_db')

    def mock_dedicated_appl_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'appl_db', filename)
        dbconnector.dedicated_dbs['APPL_DB'] = jsonfile
        appl_db = SonicV2Connector(host='127.0.0.1')
        appl_db.connect(appl_db.APPL_DB)
        return appl_db

    def clear_dedicated_mock_dbs(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = None
        dbconnector.dedicated_dbs['STATE_DB'] = None
        dbconnector.dedicated_dbs['APPL_DB'] = None

    def check_config_db(self, result, expected, tables_to_verify=None):
        if not tables_to_verify:
            tables_to_verify = self.config_db_tables_to_verify
        for table in tables_to_verify:
            assert result.get_table(table) == expected.get_table(table)

    def check_appl_db(self, result, expected):
        for table in self.appl_db_tables_to_verify:
            keys = expected.keys(expected.APPL_DB, table)
            assert keys == result.keys(result.APPL_DB, table)
            if keys is None:
                continue
            for key in keys:
                assert expected.get_all(expected.APPL_DB, key) == result.get_all(result.APPL_DB, key)

    @pytest.mark.parametrize('scenario',
                             ['empty-config',
                              'non-default-config',
                              'non-default-xoff',
                              'non-default-lossless-profile-in-pg',
                              'non-default-lossy-profile-in-pg',
                              'non-default-pg'
                             ])
    def test_mellanox_buffer_migrator_negative_cold_reboot(self, scenario):
        db_before_migrate = scenario + '-input'
        db_after_migrate = scenario + '-expected'
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        db = self.mock_dedicated_config_db(db_before_migrate)
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        expected_db = self.mock_dedicated_config_db(db_after_migrate)
        advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, self.version_list[-1])
        self.check_config_db(dbmgtr.configDB, expected_db.cfgdb)
        assert not dbmgtr.mellanox_buffer_migrator.is_buffer_config_default

    @pytest.mark.parametrize('sku_version',
                             [('ACS-MSN2700', 'version_1_0_1'),
                              ('Mellanox-SN2700', 'version_1_0_1'),
                              ('Mellanox-SN2700-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-C28D8', 'version_1_0_1'),
                              ('Mellanox-SN2700-C28D8-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-D48C8', 'version_1_0_1'),
                              ('Mellanox-SN2700-D48C8-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-D40C8S8', 'version_1_0_5'),
                              ('ACS-MSN3700', 'version_1_0_2'),
                              ('ACS-MSN3800', 'version_1_0_5'),
                              ('Mellanox-SN3800-C64', 'version_1_0_5'),
                              ('Mellanox-SN3800-D112C8', 'version_1_0_5'),
                              ('Mellanox-SN3800-D24C52', 'version_1_0_5'),
                              ('Mellanox-SN3800-D28C50', 'version_1_0_5'),
                              ('ACS-MSN4700', 'version_1_0_4')
                             ])
    @pytest.mark.parametrize('topo', ['t0', 't1'])
    def test_mellanox_buffer_migrator_for_cold_reboot(self, sku_version, topo):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        sku, start_version = sku_version
        version = start_version
        start_index = self.version_list.index(start_version)

        # start_version represents the database version from which the SKU is supported
        # For each SKU,
        # migration from any version between start_version and the current version (inclusive) to the current version will be verified
        for version in self.version_list[start_index:]:
            _ = self.mock_dedicated_config_db(self.make_db_name_by_sku_topo_version(sku, topo, version))
            import db_migrator
            dbmgtr = db_migrator.DBMigrator(None)
            dbmgtr.migrate()

            # Eventually, the config db should be migrated to the latest version
            expected_db = self.mock_dedicated_config_db(self.make_db_name_by_sku_topo_version(sku, topo, self.version_list[-1]))
            advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, self.version_list[-1])
            self.check_config_db(dbmgtr.configDB, expected_db.cfgdb)
            assert dbmgtr.mellanox_buffer_migrator.is_buffer_config_default

        self.clear_dedicated_mock_dbs()

    def mellanox_buffer_migrator_warm_reboot_runner(self, input_config_db, input_appl_db, expected_config_db, expected_appl_db, is_buffer_config_default_expected):
        expected_config_db = self.mock_dedicated_config_db(expected_config_db)
        expected_appl_db = self.mock_dedicated_appl_db(expected_appl_db)
        self.mock_dedicated_state_db()
        _ = self.mock_dedicated_config_db(input_config_db)
        _ = self.mock_dedicated_appl_db(input_appl_db)

        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        advance_version_for_expected_database(dbmgtr.configDB, expected_config_db.cfgdb, self.version_list[-1])
        assert dbmgtr.mellanox_buffer_migrator.is_buffer_config_default == is_buffer_config_default_expected
        self.check_config_db(dbmgtr.configDB, expected_config_db.cfgdb)
        self.check_appl_db(dbmgtr.appDB, expected_appl_db)

        self.clear_dedicated_mock_dbs()

    @pytest.mark.parametrize('sku',
                             ['ACS-MSN2700',
                              'Mellanox-SN2700', 'Mellanox-SN2700-Single-Pool', 'Mellanox-SN2700-C28D8', 'Mellanox-SN2700-C28D8-Single-Pool',
                              'Mellanox-SN2700-D48C8', 'Mellanox-SN2700-D48C8-Single-Pool',
                              'Mellanox-SN2700-D40C8S8',
                              'ACS-MSN3700',
                              'ACS-MSN3800',
                              'Mellanox-SN3800-C64',
                              'Mellanox-SN3800-D112C8',
                              'Mellanox-SN3800-D24C52',
                              'Mellanox-SN3800-D28C50',
                              'ACS-MSN4700'
                             ])
    @pytest.mark.parametrize('topo', ['t0', 't1'])
    def test_mellanox_buffer_migrator_for_warm_reboot(self, sku, topo):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        # Eventually, the config db should be migrated to the latest version
        expected_db_name = self.make_db_name_by_sku_topo_version(sku, topo, self.warm_reboot_to_version)
        input_db_name = self.make_db_name_by_sku_topo_version(sku, topo, self.warm_reboot_from_version)
        self.mellanox_buffer_migrator_warm_reboot_runner(input_db_name, input_db_name, expected_db_name, expected_db_name, True)

    def test_mellanox_buffer_migrator_negative_nondefault_for_warm_reboot(self):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        expected_config_db = 'non-default-config-expected'
        expected_appl_db = 'non-default-expected'
        input_config_db = 'non-default-config-input'
        input_appl_db = 'non-default-input'
        self.mellanox_buffer_migrator_warm_reboot_runner(input_config_db, input_appl_db, expected_config_db, expected_appl_db, False)

    @pytest.mark.parametrize('buffer_model', ['traditional', 'dynamic'])
    @pytest.mark.parametrize('ingress_pools', ['double-pools', 'single-pool'])
    def test_mellanox_buffer_reclaiming(self, buffer_model, ingress_pools):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        db_before_migrate = 'reclaiming-buffer-' + buffer_model + '-' + ingress_pools + '-input'
        db_after_migrate = 'reclaiming-buffer-' + buffer_model + '-' + ingress_pools + '-expected'

        db = self.mock_dedicated_config_db(db_before_migrate)
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        expected_db = self.mock_dedicated_config_db(db_after_migrate)
        advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, 'version_3_0_3')
        tables_to_verify = self.config_db_tables_to_verify
        tables_to_verify.extend(['BUFFER_QUEUE', 'BUFFER_PORT_INGRESS_PROFILE_LIST', 'BUFFER_PORT_EGRESS_PROFILE_LIST'])
        self.check_config_db(dbmgtr.configDB, expected_db.cfgdb, tables_to_verify)

    def test_mellanox_buffer_reclaiming_warm_reboot(self):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        input_db_name = 'reclaiming-buffer-warmreboot-input'
        expected_db_name = 'reclaiming-buffer-warmreboot-expected'
        self.mellanox_buffer_migrator_warm_reboot_runner(input_db_name, input_db_name, expected_db_name,expected_db_name, True)


class TestAutoNegMigrator(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_port_autoneg_migrator(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'port-an-input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()

        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'port-an-expected')
        expected_db = Db()
        advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, 'version_3_0_1')

        assert dbmgtr.configDB.get_table('PORT') == expected_db.cfgdb.get_table('PORT')
        assert dbmgtr.configDB.get_table('VERSIONS') == expected_db.cfgdb.get_table('VERSIONS')

class TestInitConfigMigrator(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_init_config_feature_migration(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'feature-input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'feature-expected')
        expected_db = Db()

        resulting_table = dbmgtr.configDB.get_table('FEATURE')
        expected_table = expected_db.cfgdb.get_table('FEATURE')

        diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
        assert not diff

        assert not expected_db.cfgdb.get_table('CONTAINER_FEATURE')

class TestLacpKeyMigrator(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_lacp_key_migrator(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'portchannel-input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'portchannel-expected')
        expected_db = Db()
        advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, 'version_3_0_2')

        assert dbmgtr.configDB.get_table('PORTCHANNEL') == expected_db.cfgdb.get_table('PORTCHANNEL')
        assert dbmgtr.configDB.get_table('VERSIONS') == expected_db.cfgdb.get_table('VERSIONS')

class TestQosDBFieldValueReferenceRemoveMigrator(object):
    @classmethod
    def setup_class(cls):
        cls.config_db_tables_to_verify = ['QUEUE', 'PORT_QOS_MAP', 'BUFFER_PROFILE', 'BUFFER_PG', 'BUFFER_PORT_INGRESS_PROFILE_LIST', 'BUFFER_PORT_EGRESS_PROFILE_LIST', 'VERSIONS']
        cls.appl_db_tables_to_verify = ['BUFFER_PROFILE_TABLE:*', 'BUFFER_PG_TABLE:*', 'BUFFER_QUEUE_TABLE:*', 'BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE:*', 'BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE:*']
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def mock_dedicated_config_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'config_db', filename)
        dbconnector.dedicated_dbs['CONFIG_DB'] = jsonfile
        db = Db()
        return db

    def mock_dedicated_appl_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'appl_db', filename)
        dbconnector.dedicated_dbs['APPL_DB'] = jsonfile
        appl_db = SonicV2Connector(host='127.0.0.1')
        appl_db.connect(appl_db.APPL_DB)
        return appl_db

    def clear_dedicated_mock_dbs(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = None
        dbconnector.dedicated_dbs['APPL_DB'] = None

    def check_config_db(self, result, expected):
        for table in self.config_db_tables_to_verify:
            assert result.get_table(table) == expected.get_table(table)

    def check_appl_db(self, result, expected):
        for table in self.appl_db_tables_to_verify:
            keys = expected.keys(expected.APPL_DB, table)
            if keys is None:
                continue
            for key in keys:
                assert expected.get_all(expected.APPL_DB, key) == result.get_all(result.APPL_DB, key)

    def test_qos_buffer_migrator_for_cold_reboot(self):
        db_before_migrate = 'qos_tables_db_field_value_reference_format_3_0_1'
        db_after_migrate = 'qos_tables_db_field_value_reference_format_3_0_3'
        db = self.mock_dedicated_config_db(db_before_migrate)
        _ = self.mock_dedicated_appl_db(db_before_migrate)
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        expected_db = self.mock_dedicated_config_db(db_after_migrate)
        expected_appl_db = self.mock_dedicated_appl_db(db_after_migrate)
        advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb, 'version_3_0_3')

        self.check_config_db(dbmgtr.configDB, expected_db.cfgdb)
        self.check_appl_db(dbmgtr.appDB, expected_appl_db)
        self.clear_dedicated_mock_dbs()


class TestPfcEnableMigrator(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_pfc_enable_migrator(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'qos_map_table_input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'qos_map_table_expected')
        expected_db = Db()

        resulting_table = dbmgtr.configDB.get_table('PORT_QOS_MAP')
        expected_table = expected_db.cfgdb.get_table('PORT_QOS_MAP')

        diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
        assert not diff

class TestGlobalDscpToTcMapMigrator(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_global_dscp_to_tc_map_migrator(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'qos_map_table_global_input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.asic_type = "broadcom"
        dbmgtr.hwsku = "vs"
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'qos_map_table_global_expected')
        expected_db = Db()

        resulting_table = dbmgtr.configDB.get_table('PORT_QOS_MAP')
        expected_table = expected_db.cfgdb.get_table('PORT_QOS_MAP')

        diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
        assert not diff

        # Check port_qos_map|global is not generated on mellanox asic
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'qos_map_table_global_input')
        dbmgtr_mlnx = db_migrator.DBMigrator(None)
        dbmgtr_mlnx.asic_type = "mellanox"
        dbmgtr_mlnx.hwsku = "vs"
        dbmgtr_mlnx.migrate()
        resulting_table = dbmgtr_mlnx.configDB.get_table('PORT_QOS_MAP')
        assert resulting_table == {}
        
class TestMoveLoggerTablesInWarmUpgrade(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None
        dbconnector.dedicated_dbs['LOGLEVEL_DB'] = None
        dbconnector.dedicated_dbs['STATE_DB'] = None

    def mock_dedicated_loglevel_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'loglevel_db', filename)
        dbconnector.dedicated_dbs['LOGLEVEL_DB'] = jsonfile
        loglevel_db = SonicV2Connector(host='127.0.0.1')
        loglevel_db.connect(loglevel_db.LOGLEVEL_DB)
        return loglevel_db

    def test_move_logger_tables_in_warm_upgrade(self):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx

        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'logger_tables_input')
        dbconnector.dedicated_dbs['LOGLEVEL_DB'] = os.path.join(mock_db_path, 'loglevel_db', 'logger_tables_input')
        dbconnector.dedicated_dbs['STATE_DB'] = os.path.join(mock_db_path, 'state_db')

        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()

        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'logger_tables_expected')
        dbconnector.dedicated_dbs['LOGLEVEL_DB'] = os.path.join(mock_db_path, 'loglevel_db', 'logger_tables_expected')

        expected_db = Db()

        resulting_table = dbmgtr.configDB.get_table('LOGGER')
        expected_table = expected_db.cfgdb.get_table('LOGGER')

        diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
        assert not diff

class TestWarmUpgrade_to_2_0_2(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None

    def test_warm_upgrade_to_2_0_2(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'cross_branch_upgrade_to_version_2_0_2_input')
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'cross_branch_upgrade_to_version_2_0_2_expected')
        expected_db = Db()

        expected_db
        new_tables = ["RESTAPI", "TELEMETRY", "CONSOLE_SWITCH"]
        for table in new_tables:
            resulting_table = dbmgtr.configDB.get_table(table)
            expected_table = expected_db.cfgdb.get_table(table)
            diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
            assert not diff

class Test_Migrate_Loopback(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        dbconnector.dedicated_dbs['CONFIG_DB'] = None
        dbconnector.dedicated_dbs['APPL_DB'] = None

    def test_migrate_loopback_int(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'loopback_interface_migrate_from_1_0_1_input')
        dbconnector.dedicated_dbs['APPL_DB'] = os.path.join(mock_db_path, 'appl_db', 'loopback_interface_migrate_from_1_0_1_input')

        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, 'config_db', 'loopback_interface_migrate_from_1_0_1_expected')
        dbconnector.dedicated_dbs['APPL_DB'] = os.path.join(mock_db_path, 'appl_db', 'loopback_interface_migrate_from_1_0_1_expected')
        expected_db = Db()

        # verify migrated configDB
        resulting_table = dbmgtr.configDB.get_table("LOOPBACK_INTERFACE")
        expected_table = expected_db.cfgdb.get_table("LOOPBACK_INTERFACE")
        diff = DeepDiff(resulting_table, expected_table, ignore_order=True)
        assert not diff

        # verify migrated appDB
        expected_appl_db = SonicV2Connector(host='127.0.0.1')
        expected_appl_db.connect(expected_appl_db.APPL_DB)
        expected_keys = expected_appl_db.keys(expected_appl_db.APPL_DB, "INTF_TABLE:*")
        expected_keys.sort()
        resulting_keys = dbmgtr.appDB.keys(dbmgtr.appDB.APPL_DB, "INTF_TABLE:*")
        resulting_keys.sort()
        assert expected_keys == resulting_keys
        for key in expected_keys:
            resulting_keys = dbmgtr.appDB.get_all(dbmgtr.appDB.APPL_DB, key)
            expected_keys = expected_appl_db.get_all(expected_appl_db.APPL_DB, key)
            diff = DeepDiff(resulting_keys, expected_keys, ignore_order=True)
            assert not diff
