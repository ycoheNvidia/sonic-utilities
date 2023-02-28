#!/usr/bin/env python

import os
import copy
from unittest.mock import Mock, MagicMock, call

import pytest

from sonic_package_manager.database import PackageEntry
from sonic_package_manager.manifest import Manifest
from sonic_package_manager.metadata import Metadata
from sonic_package_manager.package import Package
from sonic_package_manager.service_creator.creator import *
from sonic_package_manager.service_creator.feature import FeatureRegistry


@pytest.fixture
def manifest():
    return Manifest.marshal({
        'package': {
            'name': 'test',
            'version': '1.0.0',
        },
        'service': {
            'name': 'test',
            'requires': ['database'],
            'after': ['database', 'swss', 'syncd'],
            'before': ['ntp-config'],
            'dependent-of': ['swss'],
            'asic-service': False,
            'host-service': True,
            'warm-shutdown': {
                'before': ['syncd'],
                'after': ['swss'],
            },
            'fast-shutdown': {
                'before': ['swss'],
            },
            'syslog': {
                'support-rate-limit': False
            }
        },
        'container': {
            'privileged': True,
            'volumes': [
                '/etc/sonic:/etc/sonic:ro'
            ]
        },
        'processes': [
            {
                'name': 'test-process',
                'reconciles': True,
            },
            {
                'name': 'test-process-2',
                'reconciles': False,
            },
            {
                'name': 'test-process-3',
                'reconciles': True,
            },
        ]
    })


@pytest.fixture()
def service_creator(mock_feature_registry,
                    mock_sonic_db,
                    mock_cli_gen,
                    mock_config_mgmt):
    yield ServiceCreator(
        mock_feature_registry,
        mock_sonic_db,
        mock_cli_gen,
        mock_config_mgmt
    )


def test_service_creator(sonic_fs, manifest, service_creator, package_manager):
    entry = PackageEntry('test', 'azure/sonic-test')
    package = Package(entry, Metadata(manifest))
    installed_packages = package_manager._get_installed_packages_and(package)
    service_creator.create(package)
    service_creator.generate_shutdown_sequence_files(installed_packages)

    assert sonic_fs.exists(os.path.join(ETC_SONIC_PATH, 'swss_dependent'))
    assert sonic_fs.exists(os.path.join(DOCKER_CTL_SCRIPT_LOCATION, 'test.sh'))
    assert sonic_fs.exists(os.path.join(SERVICE_MGMT_SCRIPT_LOCATION, 'test.sh'))
    assert sonic_fs.exists(os.path.join(SYSTEMD_LOCATION, 'test.service'))

    def read_file(name):
        with open(os.path.join(ETC_SONIC_PATH, name)) as file:
            return file.read()

    assert read_file('warm-reboot_order') == 'swss teamd test syncd'
    assert read_file('fast-reboot_order') == 'teamd test swss syncd'
    assert read_file('test_reconcile') == 'test-process test-process-3'


def test_service_creator_with_timer_unit(sonic_fs, manifest, service_creator):
    entry = PackageEntry('test', 'azure/sonic-test')
    package = Package(entry, Metadata(manifest))
    service_creator.create(package)

    assert not sonic_fs.exists(os.path.join(SYSTEMD_LOCATION, 'test.timer'))

    manifest['service']['delayed'] = True
    package = Package(entry, Metadata(manifest))
    service_creator.create(package)

    assert sonic_fs.exists(os.path.join(SYSTEMD_LOCATION, 'test.timer'))


def test_service_creator_with_debug_dump(sonic_fs, manifest, service_creator):
    entry = PackageEntry('test', 'azure/sonic-test')
    package = Package(entry, Metadata(manifest))
    service_creator.create(package)

    assert not sonic_fs.exists(os.path.join(DEBUG_DUMP_SCRIPT_LOCATION, 'test'))

    manifest['package']['debug-dump'] = '/some/command'
    package = Package(entry, Metadata(manifest))
    service_creator.create(package)

    assert sonic_fs.exists(os.path.join(DEBUG_DUMP_SCRIPT_LOCATION, 'test'))


def test_service_creator_yang(sonic_fs, manifest, mock_sonic_db,
                              mock_config_mgmt, service_creator):
    test_yang = 'TEST YANG'
    test_yang_module = 'sonic-test'

    mock_connector = Mock()
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    mock_connector.get_table = Mock(return_value={'key_a': {'field_1': 'value_1'}})
    mock_connector.get_config = Mock(return_value={
        'TABLE_A': mock_connector.get_table(''),
        'TABLE_B': mock_connector.get_table(''),
        'TABLE_C': mock_connector.get_table(''),
    })

    entry = PackageEntry('test', 'azure/sonic-test')
    package = Package(entry, Metadata(manifest, yang_module_str=test_yang))
    service_creator.create(package)

    mock_config_mgmt.add_module.assert_called_with(test_yang)
    mock_config_mgmt.get_module_name = Mock(return_value=test_yang_module)

    manifest['package']['init-cfg'] = {
        'TABLE_A': {
            'key_a': {
                'field_1': 'new_value_1',
                'field_2': 'value_2'
            },
        },
    }
    package = Package(entry, Metadata(manifest, yang_module_str=test_yang))

    service_creator.create(package)

    mock_config_mgmt.add_module.assert_called_with(test_yang)

    mock_connector.mod_entry.assert_called_once_with(
        'TABLE_A', 'key_a', {'field_1': 'value_1', 'field_2': 'value_2'}
    )

    mock_config_mgmt.sy.confDbYangMap = {
        'TABLE_A': {'module': test_yang_module}
    }

    service_creator.remove(package)
    mock_connector.set_entry.assert_called_with('TABLE_A', 'key_a', None)
    mock_config_mgmt.remove_module.assert_called_with(test_yang_module)


def test_service_creator_autocli(sonic_fs, manifest, mock_cli_gen,
                                 mock_config_mgmt, service_creator):
    test_yang = 'TEST YANG'
    test_yang_module = 'sonic-test'

    manifest['cli']['auto-generate-show'] = True
    manifest['cli']['auto-generate-config'] = True

    entry = PackageEntry('test', 'azure/sonic-test')
    package = Package(entry, Metadata(manifest, yang_module_str=test_yang))
    mock_config_mgmt.get_module_name = Mock(return_value=test_yang_module)
    service_creator.create(package)

    mock_cli_gen.generate_cli_plugin.assert_has_calls(
        [
            call('show', test_yang_module),
            call('config', test_yang_module),
        ],
        any_order=True
    )

    service_creator.remove(package)
    mock_cli_gen.remove_cli_plugin.assert_has_calls(
        [
            call('show', test_yang_module),
            call('config', test_yang_module),
        ],
        any_order=True
    )


def test_feature_registration(mock_sonic_db, manifest):
    mock_connector = Mock()
    mock_connector.get_entry = Mock(return_value={})
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_connector)
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.register(manifest)
    mock_connector.set_entry.assert_called_with('FEATURE', 'test', {
        'state': 'disabled',
        'auto_restart': 'enabled',
        'high_mem_alert': 'disabled',
        'set_owner': 'local',
        'has_per_asic_scope': 'False',
        'has_global_scope': 'True',
        'has_timer': 'False',
        'check_up_status': 'False',
        'support_syslog_rate_limit': 'False',
    })


def test_feature_update(mock_sonic_db, manifest):
    curr_feature_config = {
        'state': 'enabled',
        'auto_restart': 'enabled',
        'high_mem_alert': 'disabled',
        'set_owner': 'local',
        'has_per_asic_scope': 'False',
        'has_global_scope': 'True',
        'has_timer': 'False',
        'check_up_status': 'False',
        'support_syslog_rate_limit': 'False',
    }
    mock_connector = Mock()
    mock_connector.get_entry = Mock(return_value=curr_feature_config)
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    feature_registry = FeatureRegistry(mock_sonic_db)

    new_manifest = copy.deepcopy(manifest)
    new_manifest['service']['name'] = 'test_new'
    new_manifest['service']['delayed'] = True

    feature_registry.update(manifest, new_manifest)

    mock_connector.set_entry.assert_has_calls([
        call('FEATURE', 'test', None),
        call('FEATURE', 'test_new', {
            'state': 'enabled',
            'auto_restart': 'enabled',
            'high_mem_alert': 'disabled',
            'set_owner': 'local',
            'has_per_asic_scope': 'False',
            'has_global_scope': 'True',
            'has_timer': 'True',
            'check_up_status': 'False',
            'support_syslog_rate_limit': 'False',
        }),
    ], any_order=True)


def test_feature_registration_with_timer(mock_sonic_db, manifest):
    manifest['service']['delayed'] = True
    mock_connector = Mock()
    mock_connector.get_entry = Mock(return_value={})
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_connector)
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.register(manifest)
    mock_connector.set_entry.assert_called_with('FEATURE', 'test', {
        'state': 'disabled',
        'auto_restart': 'enabled',
        'high_mem_alert': 'disabled',
        'set_owner': 'local',
        'has_per_asic_scope': 'False',
        'has_global_scope': 'True',
        'has_timer': 'True',
        'check_up_status': 'False',
        'support_syslog_rate_limit': 'False',
    })


def test_feature_registration_with_non_default_owner(mock_sonic_db, manifest):
    mock_connector = Mock()
    mock_connector.get_entry = Mock(return_value={})
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_connector)
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.register(manifest, owner='kube')
    mock_connector.set_entry.assert_called_with('FEATURE', 'test', {
        'state': 'disabled',
        'auto_restart': 'enabled',
        'high_mem_alert': 'disabled',
        'set_owner': 'kube',
        'has_per_asic_scope': 'False',
        'has_global_scope': 'True',
        'has_timer': 'False',
        'check_up_status': 'False',
        'support_syslog_rate_limit': 'False',
    })


class AutoTSHelp:
    """ Helper class for Auto TS Feature Registry Tests
    """
    GLOBAL_STATE = {}

    @classmethod
    def get_entry(cls, table, key):
        if table == "AUTO_TECHSUPPORT" and key == "GLOBAL":
            return AutoTSHelp.GLOBAL_STATE
        elif table == "AUTO_TECHSUPPORT_FEATURE" and key == "test":
            return {"state" : "enabled", "rate_limit_interval" : "600"}
        else:
            return {}

    @classmethod
    def get_entry_running_cfg(cls, table, key):
        if table == "AUTO_TECHSUPPORT_FEATURE" and key == "test":
            return {"state" : "disabled", "rate_limit_interval" : "1000", "available_mem_threshold": "20.0"}
        else:
            return {}


def test_auto_ts_global_disabled(mock_sonic_db, manifest):
    mock_init_cfg = Mock()
    AutoTSHelp.GLOBAL_STATE = {"state" : "disabled"}
    mock_init_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry)
    mock_sonic_db.get_connectors = Mock(return_value=[mock_init_cfg])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_init_cfg)
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.register(manifest)
    mock_init_cfg.set_entry.assert_any_call("AUTO_TECHSUPPORT_FEATURE", "test", {
            "state" : "disabled",
            "rate_limit_interval" : "600",
            "available_mem_threshold": "10.0"
        }
    )


def test_auto_ts_global_enabled(mock_sonic_db, manifest):
    mock_init_cfg = Mock()
    AutoTSHelp.GLOBAL_STATE = {"state" : "enabled"}
    mock_init_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry)
    mock_sonic_db.get_connectors = Mock(return_value=[mock_init_cfg])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_init_cfg)
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.register(manifest)
    mock_init_cfg.set_entry.assert_any_call("AUTO_TECHSUPPORT_FEATURE", "test", {
            "state" : "enabled",
            "rate_limit_interval" : "600",
            "available_mem_threshold": "10.0"
        }
    )


def test_auto_ts_deregister(mock_sonic_db):
    mock_connector = Mock()
    mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.deregister("test")
    mock_connector.set_entry.assert_any_call("AUTO_TECHSUPPORT_FEATURE", "test", None)


def test_auto_ts_feature_update_flow(mock_sonic_db, manifest):
    new_manifest = copy.deepcopy(manifest)
    new_manifest['service']['name'] = 'test_new'
    new_manifest['service']['delayed'] = True

    AutoTSHelp.GLOBAL_STATE = {"state" : "enabled"}
    # Mock init_cfg connector
    mock_init_cfg = Mock()
    mock_init_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry)

    # Mock running/peristent cfg connector
    mock_other_cfg = Mock()
    mock_other_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry_running_cfg)

    # Setup sonic_db class
    mock_sonic_db.get_connectors = Mock(return_value=[mock_init_cfg, mock_other_cfg])
    mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_init_cfg)

    feature_registry = FeatureRegistry(mock_sonic_db)
    feature_registry.update(manifest, new_manifest)

    mock_init_cfg.set_entry.assert_has_calls(
        [
            call("AUTO_TECHSUPPORT_FEATURE", "test", None),
            call("AUTO_TECHSUPPORT_FEATURE", "test_new", {
                    "state" : "enabled",
                    "rate_limit_interval" : "600",
                    "available_mem_threshold": "10.0"
                })
        ],
        any_order = True
    )

    mock_other_cfg.set_entry.assert_has_calls(
        [
            call("AUTO_TECHSUPPORT_FEATURE", "test", None),
            call("AUTO_TECHSUPPORT_FEATURE", "test_new", {
                    "state" : "disabled",
                    "rate_limit_interval" : "1000",
                    "available_mem_threshold": "20.0"
                })
        ],
        any_order = True
    )


class TestSyslogRateLimit:
    """ Helper class for Syslog rate limit Tests
    """
    @classmethod
    def get_entry_running_cfg(cls, table, key):
        if table == "SYSLOG_CONFIG_FEATURE" and key == "test":
            return {"rate_limit_burst" : "10000", "rate_limit_interval" : "20"}
        else:
            return {}

    def test_rate_limit_register(self, mock_sonic_db, manifest):
        mock_init_cfg = Mock()
        mock_init_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry)
        mock_sonic_db.get_connectors = Mock(return_value=[mock_init_cfg])
        mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_init_cfg)
        feature_registry = FeatureRegistry(mock_sonic_db)
        new_manifest = copy.deepcopy(manifest)
        new_manifest['service']['syslog']['support-rate-limit'] = True
        feature_registry.register(new_manifest)
        mock_init_cfg.set_entry.assert_any_call("SYSLOG_CONFIG_FEATURE", "test", {
                "rate_limit_interval" : "300",
                "rate_limit_burst" : "20000"
            }
        )

    def test_rate_limit_deregister(self, mock_sonic_db):
        mock_connector = Mock()
        mock_sonic_db.get_connectors = Mock(return_value=[mock_connector])
        feature_registry = FeatureRegistry(mock_sonic_db)
        feature_registry.deregister("test")
        mock_connector.set_entry.assert_any_call("SYSLOG_CONFIG_FEATURE", "test", None)

    def test_rate_limit_update(self, mock_sonic_db, manifest):
        rate_limit_manifest = copy.deepcopy(manifest)
        rate_limit_manifest['service']['syslog']['support-rate-limit'] = True
        new_rate_limit_manifest = copy.deepcopy(rate_limit_manifest)
        new_rate_limit_manifest['service']['name'] = 'test_new'
        new_rate_limit_manifest['service']['delayed'] = True

        # Mock init_cfg connector
        mock_init_cfg = Mock()
        mock_init_cfg.get_entry = Mock(side_effect=AutoTSHelp.get_entry)

        # Mock running/peristent cfg connector
        mock_other_cfg = Mock()
        mock_other_cfg.get_entry = Mock(side_effect=TestSyslogRateLimit.get_entry_running_cfg)

        # Setup sonic_db class
        mock_sonic_db.get_connectors = Mock(return_value=[mock_init_cfg, mock_other_cfg])
        mock_sonic_db.get_initial_db_connector = Mock(return_value=mock_init_cfg)

        feature_registry = FeatureRegistry(mock_sonic_db)
        feature_registry.update(rate_limit_manifest, new_rate_limit_manifest)

        mock_init_cfg.set_entry.assert_has_calls(
            [
                call("SYSLOG_CONFIG_FEATURE", "test", None),
                call("SYSLOG_CONFIG_FEATURE", "test_new", {
                        "rate_limit_interval" : "300",
                        "rate_limit_burst" : "20000"
                    })
            ],
            any_order = True
        )

        mock_other_cfg.set_entry.assert_has_calls(
            [
                call("SYSLOG_CONFIG_FEATURE", "test", None),
                call("SYSLOG_CONFIG_FEATURE", "test_new", {
                        "rate_limit_interval" : "20",
                        "rate_limit_burst" : "10000"
                    })
            ],
            any_order = True
        )
