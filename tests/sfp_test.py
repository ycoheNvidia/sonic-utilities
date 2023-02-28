import sys
import os
from click.testing import CliRunner

from .mock_tables import dbconnector

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

import show.main as show

test_sfp_eeprom_with_dom_output = """\
Ethernet0: SFP EEPROM detected
        Application Advertisement: N/A
        Connector: No separable connector
        Encoding: 64B66B
        Extended Identifier: Power Class 3(2.5W max), CDR present in Rx Tx
        Extended RateSelect Compliance: QSFP+ Rate Select Version 1
        Identifier: QSFP28 or later
        Length Cable Assembly(m): 3
        Nominal Bit Rate(100Mbs): 255
        Specification compliance:
                10/40G Ethernet Compliance Code: 40G Active Cable (XLPPI)
        Vendor Date Code(YYYY-MM-DD Lot): 2017-01-13
        Vendor Name: Mellanox
        Vendor OUI: 00-02-c9
        Vendor PN: MFA1A00-C003
        Vendor Rev: AC
        Vendor SN: MT1706FT02064
        ChannelMonitorValues:
                RX1Power: 0.3802dBm
                RX2Power: -0.4871dBm
                RX3Power: -0.0860dBm
                RX4Power: 0.3830dBm
                TX1Bias: 6.7500mA
                TX2Bias: 6.7500mA
                TX3Bias: 6.7500mA
                TX4Bias: 6.7500mA
        ChannelThresholdValues:
                RxPowerHighAlarm  : 3.4001dBm
                RxPowerHighWarning: 2.4000dBm
                RxPowerLowAlarm   : -13.5067dBm
                RxPowerLowWarning : -9.5001dBm
                TxBiasHighAlarm   : 10.0000mA
                TxBiasHighWarning : 9.5000mA
                TxBiasLowAlarm    : 0.5000mA
                TxBiasLowWarning  : 1.0000mA
        ModuleMonitorValues:
                Temperature: 30.9258C
                Vcc: 3.2824Volts
        ModuleThresholdValues:
                TempHighAlarm  : 75.0000C
                TempHighWarning: 70.0000C
                TempLowAlarm   : -5.0000C
                TempLowWarning : 0.0000C
                VccHighAlarm   : 3.6300Volts
                VccHighWarning : 3.4650Volts
                VccLowAlarm    : 2.9700Volts
                VccLowWarning  : 3.1349Volts
"""

test_qsfp_dd_eeprom_with_dom_output = """\
Ethernet8: SFP EEPROM detected
        Application Advertisement: 400GAUI-8 C2M (Annex 120E) - Active Cable assembly with BER < 2.6x10^-4
				   IB EDR (Arch.Spec.Vol.2) - Active Cable assembly with BER < 5x10^-5
				   IB QDR (Arch.Spec.Vol.2) - Active Cable assembly with BER < 10^-12
        Connector: No separable connector
        Encoding: Not supported for CMIS cables
        Extended Identifier: Power Class 1(10.0W Max)
        Extended RateSelect Compliance: Not supported for CMIS cables
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Length Cable Assembly(m): 10
        Nominal Bit Rate(100Mbs): Not supported for CMIS cables
        Specification compliance: Not supported for CMIS cables
        Vendor Date Code(YYYY-MM-DD Lot): 2020-05-22
        Vendor Name: INNOLIGHT
        Vendor OUI: 44-7c-7f
        Vendor PN: C-DQ8FNM010-N00
        Vendor Rev: 2A
        Vendor SN: INKAO2900002A
        ChannelMonitorValues:
                RX1Power: -3.8595dBm
                RX2Power: 8.1478dBm
                RX3Power: -22.9243dBm
                RX4Power: 1.175dBm
                RX5Power: 1.2421dBm
                RX6Power: 8.1489dBm
                RX7Power: -3.5962dBm
                RX8Power: -3.6131dBm
                TX1Bias: 17.4760mA
                TX1Power: 1.175dBm
                TX2Bias: 17.4760mA
                TX2Power: 1.175dBm
                TX3Bias: 0.0000mA
                TX3Power: 1.175dBm
                TX4Bias: 0.0000mA
                TX4Power: 1.175dBm
                TX5Bias: 0.0000mA
                TX5Power: 1.175dBm
                TX6Bias: 8.2240mA
                TX6Power: 1.175dBm
                TX7Bias: 8.2240mA
                TX7Power: 1.175dBm
                TX8Bias: 8.2240mA
                TX8Power: 1.175dBm
        ChannelThresholdValues:
                RxPowerHighAlarm  : 6.9999dBm
                RxPowerHighWarning: 4.9999dBm
                RxPowerLowAlarm   : -11.9044dBm
                RxPowerLowWarning : -8.9008dBm
                TxBiasHighAlarm   : 14.9960mA
                TxBiasHighWarning : 12.9980mA
                TxBiasLowAlarm    : 4.4960mA
                TxBiasLowWarning  : 5.0000mA
                TxPowerHighAlarm  : 6.9999dBm
                TxPowerHighWarning: 4.9999dBm
                TxPowerLowAlarm   : -10.5012dBm
                TxPowerLowWarning : -7.5007dBm
        ModuleMonitorValues:
                Temperature: 44.9883C
                Vcc: 3.2999Volts
        ModuleThresholdValues:
                TempHighAlarm  : 80.0000C
                TempHighWarning: 75.0000C
                TempLowAlarm   : -10.0000C
                TempLowWarning : -5.0000C
                VccHighAlarm   : 3.6352Volts
                VccHighWarning : 3.4672Volts
                VccLowAlarm    : 2.9696Volts
                VccLowWarning  : 3.1304Volts
"""

test_sfp_eeprom_output = """\
Ethernet0: SFP EEPROM detected
        Application Advertisement: N/A
        Connector: No separable connector
        Encoding: 64B66B
        Extended Identifier: Power Class 3(2.5W max), CDR present in Rx Tx
        Extended RateSelect Compliance: QSFP+ Rate Select Version 1
        Identifier: QSFP28 or later
        Length Cable Assembly(m): 3
        Nominal Bit Rate(100Mbs): 255
        Specification compliance:
                10/40G Ethernet Compliance Code: 40G Active Cable (XLPPI)
        Vendor Date Code(YYYY-MM-DD Lot): 2017-01-13
        Vendor Name: Mellanox
        Vendor OUI: 00-02-c9
        Vendor PN: MFA1A00-C003
        Vendor Rev: AC
        Vendor SN: MT1706FT02064
"""

test_qsfp_dd_eeprom_output = """\
Ethernet8: SFP EEPROM detected
        Application Advertisement: 400GAUI-8 C2M (Annex 120E) - Active Cable assembly with BER < 2.6x10^-4
				   IB EDR (Arch.Spec.Vol.2) - Active Cable assembly with BER < 5x10^-5
				   IB QDR (Arch.Spec.Vol.2) - Active Cable assembly with BER < 10^-12
        Connector: No separable connector
        Encoding: Not supported for CMIS cables
        Extended Identifier: Power Class 1(10.0W Max)
        Extended RateSelect Compliance: Not supported for CMIS cables
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Length Cable Assembly(m): 10
        Nominal Bit Rate(100Mbs): Not supported for CMIS cables
        Specification compliance: Not supported for CMIS cables
        Vendor Date Code(YYYY-MM-DD Lot): 2020-05-22
        Vendor Name: INNOLIGHT
        Vendor OUI: 44-7c-7f
        Vendor PN: C-DQ8FNM010-N00
        Vendor Rev: 2A
        Vendor SN: INKAO2900002A
"""

test_qsfp_dd_eeprom_adv_app_output = """\
Ethernet40: SFP EEPROM detected
        Application Advertisement: 400G CR8 - Host Assign (0x1) - Copper cable - Media Assign (0x2)
                                   200GBASE-CR4 (Clause 136) - Host Assign (Unknown) - Unknown - Media Assign (Unknown)
        Connector: No separable connector
        Encoding: Not supported for CMIS cables
        Extended Identifier: Power Class 1(10.0W Max)
        Extended RateSelect Compliance: Not supported for CMIS cables
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Length Cable Assembly(m): 10
        Nominal Bit Rate(100Mbs): Not supported for CMIS cables
        Specification compliance: Not supported for CMIS cables
        Vendor Date Code(YYYY-MM-DD Lot): 2020-05-22
        Vendor Name: INNOLIGHT
        Vendor OUI: 44-7c-7f
        Vendor PN: C-DQ8FNM010-N00
        Vendor Rev: 2A
        Vendor SN: INKAO2900002A
"""

test_qsfp_dd_pm_output = """\
Ethernet44:
    Parameter        Unit    Min       Avg       Max       Threshold    Threshold    Threshold     Threshold    Threshold    Threshold
                                                           High         High         Crossing      Low          Low          Crossing
                                                           Alarm        Warning      Alert-High    Alarm        Warning      Alert-Low
    ---------------  ------  --------  --------  --------  -----------  -----------  ------------  -----------  -----------  -----------
    Tx Power         dBm     -8.22     -8.23     -8.24     -5.0         -6.0         False         -16.99       -16.003      False
    Rx Total Power   dBm     -10.61    -10.62    -10.62    2.0          0.0          False         -21.0        -18.0        False
    Rx Signal Power  dBm     -40.0     0.0       40.0      13.0         10.0         True          -18.0        -15.0        True
    CD-short link    ps/nm   0.0       0.0       0.0       1000.0       500.0        False         -1000.0      -500.0       False
    PDL              dB      0.5       0.6       0.6       4.0          4.0          False         0.0          0.0          False
    OSNR             dB      36.5      36.5      36.5      99.0         99.0         False         0.0          0.0          False
    eSNR             dB      30.5      30.5      30.5      99.0         99.0         False         0.0          0.0          False
    CFO              MHz     54.0      70.0      121.0     3800.0       3800.0       False         -3800.0      -3800.0      False
    DGD              ps      5.37      5.56      5.81      7.0          7.0          False         0.0          0.0          False
    SOPMD            ps^2    0.0       0.0       0.0       655.35       655.35       False         0.0          0.0          False
    SOP ROC          krad/s  1.0       1.0       2.0       N/A          N/A          N/A           N/A          N/A          N/A
    Pre-FEC BER      N/A     4.58E-04  4.66E-04  5.76E-04  1.25E-02     1.10E-02     0.0           0.0          0.0          0.0
    Post-FEC BER     N/A     0.0       0.0       0.0       1000.0       1.0          False         0.0          0.0          False
    EVM              %       100.0     100.0     100.0     N/A          N/A          N/A           N/A          N/A          N/A
"""

test_cmis_eeprom_output = """\
Ethernet64: SFP EEPROM detected
        Active Firmware: X.X
        Active application selected code assigned to host lane 1: 1
        Active application selected code assigned to host lane 2: 1
        Active application selected code assigned to host lane 3: 1
        Active application selected code assigned to host lane 4: 1
        Active application selected code assigned to host lane 5: 1
        Active application selected code assigned to host lane 6: 1
        Active application selected code assigned to host lane 7: 1
        Active application selected code assigned to host lane 8: 1
        Application Advertisement: 400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, DWDM, amplified - Media Assign (0x1)
                                   400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, Single Wavelength, Unamplified - Media Assign (0x1)
                                   100GAUI-2 C2M (Annex 135G) - Host Assign (0x55) - 400ZR, DWDM, amplified - Media Assign (0x1)
        CMIS Rev: 4.1
        Connector: LC
        Encoding: N/A
        Extended Identifier: Power Class 8 (20.0W Max)
        Extended RateSelect Compliance: N/A
        Host Lane Count: 8
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Inactive Firmware: X.X
        Length Cable Assembly(m): 0.0
        Media Interface Technology: 1550 nm DFB
        Media Lane Count: 1
        Module Hardware Rev: X.X
        Nominal Bit Rate(100Mbs): 0
        Specification compliance: sm_media_interface
        Supported Max Laser Frequency: 196100
        Supported Max TX Power: 4.0
        Supported Min Laser Frequency: 191300
        Supported Min TX Power: -22.9
        Vendor Date Code(YYYY-MM-DD Lot): 2021-11-19
        Vendor Name: XXXX
        Vendor OUI: XX-XX-XX
        Vendor PN: XXX
        Vendor Rev: XX
        Vendor SN: 0123456789
"""

test_sfp_eeprom_dom_all_output = """\
Ethernet0: SFP EEPROM detected
        Application Advertisement: N/A
        Connector: No separable connector
        Encoding: 64B66B
        Extended Identifier: Power Class 3(2.5W max), CDR present in Rx Tx
        Extended RateSelect Compliance: QSFP+ Rate Select Version 1
        Identifier: QSFP28 or later
        Length Cable Assembly(m): 3
        Nominal Bit Rate(100Mbs): 255
        Specification compliance:
                10/40G Ethernet Compliance Code: 40G Active Cable (XLPPI)
        Vendor Date Code(YYYY-MM-DD Lot): 2017-01-13
        Vendor Name: Mellanox
        Vendor OUI: 00-02-c9
        Vendor PN: MFA1A00-C003
        Vendor Rev: AC
        Vendor SN: MT1706FT02064
        ChannelMonitorValues:
                RX1Power: 0.3802dBm
                RX2Power: -0.4871dBm
                RX3Power: -0.0860dBm
                RX4Power: 0.3830dBm
                TX1Bias: 6.7500mA
                TX2Bias: 6.7500mA
                TX3Bias: 6.7500mA
                TX4Bias: 6.7500mA
        ChannelThresholdValues:
                RxPowerHighAlarm  : 3.4001dBm
                RxPowerHighWarning: 2.4000dBm
                RxPowerLowAlarm   : -13.5067dBm
                RxPowerLowWarning : -9.5001dBm
                TxBiasHighAlarm   : 10.0000mA
                TxBiasHighWarning : 9.5000mA
                TxBiasLowAlarm    : 0.5000mA
                TxBiasLowWarning  : 1.0000mA
        ModuleMonitorValues:
                Temperature: 30.9258C
                Vcc: 3.2824Volts
        ModuleThresholdValues:
                TempHighAlarm  : 75.0000C
                TempHighWarning: 70.0000C
                TempLowAlarm   : -5.0000C
                TempLowWarning : 0.0000C
                VccHighAlarm   : 3.6300Volts
                VccHighWarning : 3.4650Volts
                VccLowAlarm    : 2.9700Volts
                VccLowWarning  : 3.1349Volts

Ethernet4: SFP EEPROM Not detected

Ethernet64: SFP EEPROM detected
        Active Firmware: X.X
        Active application selected code assigned to host lane 1: 1
        Active application selected code assigned to host lane 2: 1
        Active application selected code assigned to host lane 3: 1
        Active application selected code assigned to host lane 4: 1
        Active application selected code assigned to host lane 5: 1
        Active application selected code assigned to host lane 6: 1
        Active application selected code assigned to host lane 7: 1
        Active application selected code assigned to host lane 8: 1
        Application Advertisement: 400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, DWDM, amplified - Media Assign (0x1)
                                   400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, Single Wavelength, Unamplified - Media Assign (0x1)
                                   100GAUI-2 C2M (Annex 135G) - Host Assign (0x55) - 400ZR, DWDM, amplified - Media Assign (0x1)
        CMIS Rev: 4.1
        Connector: LC
        Encoding: N/A
        Extended Identifier: Power Class 8 (20.0W Max)
        Extended RateSelect Compliance: N/A
        Host Lane Count: 8
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Inactive Firmware: X.X
        Length Cable Assembly(m): 0.0
        Media Interface Technology: 1550 nm DFB
        Media Lane Count: 1
        Module Hardware Rev: X.X
        Nominal Bit Rate(100Mbs): 0
        Specification compliance: sm_media_interface
        Supported Max Laser Frequency: 196100
        Supported Max TX Power: 4.0
        Supported Min Laser Frequency: 191300
        Supported Min TX Power: -22.9
        Vendor Date Code(YYYY-MM-DD Lot): 2021-11-19
        Vendor Name: XXXX
        Vendor OUI: XX-XX-XX
        Vendor PN: XXX
        Vendor Rev: XX
        Vendor SN: 0123456789
        ChannelMonitorValues:
                RX1Power: 0.3802dBm
                RX2Power: -0.4871dBm
                RX3Power: -0.0860dBm
                RX4Power: 0.3830dBm
                TX1Bias: 6.7500mA
                TX2Bias: 6.7500mA
                TX3Bias: 6.7500mA
                TX4Bias: 6.7500mA
        ChannelThresholdValues:
                RxPowerHighAlarm  : 3.4001dBm
                RxPowerHighWarning: 2.4000dBm
                RxPowerLowAlarm   : -13.5067dBm
                RxPowerLowWarning : -9.5001dBm
                TxBiasHighAlarm   : 10.0000mA
                TxBiasHighWarning : 9.5000mA
                TxBiasLowAlarm    : 0.5000mA
                TxBiasLowWarning  : 1.0000mA
        ModuleMonitorValues:
                Temperature: 30.9258C
                Vcc: 3.2824Volts
        ModuleThresholdValues:
                TempHighAlarm  : 75.0000C
                TempHighWarning: 70.0000C
                TempLowAlarm   : -5.0000C
                TempLowWarning : 0.0000C
                VccHighAlarm   : 3.6300Volts
                VccHighWarning : 3.4650Volts
                VccLowAlarm    : 2.9700Volts
                VccLowWarning  : 3.1349Volts
"""

test_sfp_eeprom_all_output = """\
Ethernet0: SFP EEPROM detected
        Application Advertisement: N/A
        Connector: No separable connector
        Encoding: 64B66B
        Extended Identifier: Power Class 3(2.5W max), CDR present in Rx Tx
        Extended RateSelect Compliance: QSFP+ Rate Select Version 1
        Identifier: QSFP28 or later
        Length Cable Assembly(m): 3
        Nominal Bit Rate(100Mbs): 255
        Specification compliance:
                10/40G Ethernet Compliance Code: 40G Active Cable (XLPPI)
        Vendor Date Code(YYYY-MM-DD Lot): 2017-01-13
        Vendor Name: Mellanox
        Vendor OUI: 00-02-c9
        Vendor PN: MFA1A00-C003
        Vendor Rev: AC
        Vendor SN: MT1706FT02064

Ethernet4: SFP EEPROM Not detected

Ethernet64: SFP EEPROM detected
        Active Firmware: X.X
        Active application selected code assigned to host lane 1: 1
        Active application selected code assigned to host lane 2: 1
        Active application selected code assigned to host lane 3: 1
        Active application selected code assigned to host lane 4: 1
        Active application selected code assigned to host lane 5: 1
        Active application selected code assigned to host lane 6: 1
        Active application selected code assigned to host lane 7: 1
        Active application selected code assigned to host lane 8: 1
        Application Advertisement: 400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, DWDM, amplified - Media Assign (0x1)
                                   400GAUI-8 C2M (Annex 120E) - Host Assign (0x1) - 400ZR, Single Wavelength, Unamplified - Media Assign (0x1)
                                   100GAUI-2 C2M (Annex 135G) - Host Assign (0x55) - 400ZR, DWDM, amplified - Media Assign (0x1)
        CMIS Rev: 4.1
        Connector: LC
        Encoding: N/A
        Extended Identifier: Power Class 8 (20.0W Max)
        Extended RateSelect Compliance: N/A
        Host Lane Count: 8
        Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        Inactive Firmware: X.X
        Length Cable Assembly(m): 0.0
        Media Interface Technology: 1550 nm DFB
        Media Lane Count: 1
        Module Hardware Rev: X.X
        Nominal Bit Rate(100Mbs): 0
        Specification compliance: sm_media_interface
        Supported Max Laser Frequency: 196100
        Supported Max TX Power: 4.0
        Supported Min Laser Frequency: 191300
        Supported Min TX Power: -22.9
        Vendor Date Code(YYYY-MM-DD Lot): 2021-11-19
        Vendor Name: XXXX
        Vendor OUI: XX-XX-XX
        Vendor PN: XXX
        Vendor Rev: XX
        Vendor SN: 0123456789
"""

test_sfp_presence_all_output = """\
Port        Presence
----------  -----------
Ethernet0   Present
Ethernet4   Not present
Ethernet64  Present
"""

test_qsfp_dd_pm_all_output = """\
Ethernet0: Transceiver performance monitoring not applicable

Ethernet4: Transceiver performance monitoring not applicable

Ethernet64: Transceiver performance monitoring not applicable
"""

class TestSFP(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["PATH"] += os.pathsep + scripts_path
        os.environ["UTILITIES_UNIT_TESTING"] = "2"

    def test_sfp_presence(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet0"])
        expected = """Port       Presence
---------  ----------
Ethernet0  Present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet200"])
        expected = """Port         Presence
-----------  -----------
Ethernet200  Not present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet16"])
        expected = """Port        Presence
----------  ----------
Ethernet16  Present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet28"])
        expected = """Port        Presence
----------  ----------
Ethernet28  Present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet29"])
        expected = """Port        Presence
----------  -----------
Ethernet29  Not present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet36"])
        expected = """Port        Presence
----------  ----------
Ethernet36  Present
"""
        assert result.exit_code == 0
        assert result.output == expected

    def test_sfp_eeprom_with_dom(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet0 -d"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_with_dom_output

    def test_qsfp_dd_eeprom_with_dom(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet8 -d"])
        assert result.exit_code == 0
        assert result.output == test_qsfp_dd_eeprom_with_dom_output

    def test_sfp_eeprom(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet0"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_output

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet200"])
        result_lines = result.output.strip('\n')
        expected = "Ethernet200: SFP EEPROM Not detected"
        assert result_lines == expected

    def test_qsfp_dd_eeprom(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet8"])
        assert result.exit_code == 0
        assert result.output == test_qsfp_dd_eeprom_output

    def test_qsfp_dd_eeprom_adv_app(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet40"])
        assert result.exit_code == 0
        print(result.output)
        assert result.output == test_qsfp_dd_eeprom_adv_app_output

    def test_cmis_info(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["info"], ["Ethernet64"])
        assert result.exit_code == 0
        assert result.output == test_cmis_eeprom_output

    def test_rj45_eeprom(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet36"])
        result_lines = result.output.strip('\n')
        expected = "Ethernet36: SFP EEPROM is not applicable for RJ45 port"
        assert result_lines == expected

    def test_qsfp_dd_pm(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["pm"], ["Ethernet44"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_qsfp_dd_pm_output

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["pm"], ["Ethernet200"])
        result_lines = result.output.strip('\n')
        expected = "Ethernet200: Transceiver performance monitoring not applicable"
        assert result_lines == expected

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = ""

class Test_multiAsic_SFP(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["PATH"] += os.pathsep + scripts_path
        os.environ["UTILITIES_UNIT_TESTING"] = "2"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = "multi_asic"

    def test_sfp_presence_with_ns(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet0 -n asic0"])
        expected = """Port       Presence
---------  ----------
Ethernet0  Present
"""
        assert result.exit_code == 0
        assert result.output == expected

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"], ["Ethernet200 -n asic0"])
        expected = """Port         Presence
-----------  -----------
Ethernet200  Not present
"""
        assert result.exit_code == 0
        assert result.output == expected

    def test_sfp_presence_all(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["presence"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_presence_all_output

    def test_sfp_eeprom_with_dom_with_ns(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet0 -d -n asic0"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_with_dom_output

    def test_sfp_eeprom_with_ns(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet0 -n asic0"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_output

        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["Ethernet200 -n asic0"])
        result_lines = result.output.strip('\n')
        expected = "Ethernet200: SFP EEPROM Not detected"
        assert result_lines == expected

    def test_qsfp_dd_pm_with_ns(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["pm"], ["Ethernet0 -n asic0"])
        result_lines = result.output.strip('\n')
        expected = "Ethernet0: Transceiver performance monitoring not applicable"
        assert result_lines == expected

    def test_cmis_sfp_info_with_ns(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["info"], ["Ethernet64 -n asic1"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_cmis_eeprom_output

    def test_sfp_eeprom_all(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_all_output

    def test_sfp_info_all(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["info"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_all_output

    def test_sfp_eeprom_dom_all(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["eeprom"], ["-d"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_sfp_eeprom_dom_all_output

    def test_is_rj45_port(self):
        import utilities_common.platform_sfputil_helper as platform_sfputil_helper
        platform_sfputil_helper.platform_chassis = None
        if 'sonic_platform' in sys.modules:
            sys.modules.pop('sonic_platform')
        assert platform_sfputil_helper.is_rj45_port("Ethernet0") == False

    def test_qsfp_dd_pm_all(self):
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["interfaces"].commands["transceiver"].commands["pm"])
        assert result.exit_code == 0
        assert "\n".join([ l.rstrip() for l in result.output.split('\n')]) == test_qsfp_dd_pm_all_output

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = ""
