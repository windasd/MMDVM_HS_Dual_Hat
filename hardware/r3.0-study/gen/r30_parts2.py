"""Meshtastic (RAK4631 pin map), GPS (MAX-M10S) and power (1S4P) sheets of the r3.0 study board."""
from r30_parts import C, FP_C0603, FP_C0805, FP_C1206, LED, P, R

FP_UFL = 'Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical'
FP_NFET = 'Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET'


# ============================================================================== Meshtastic
def meshtastic():
    rak = {
        '1': 'MESH_VBUS', '2': 'MESH_USB_DM', '3': 'MESH_USB_DP',
        '4': 'SDA_MESH', '5': 'SCL_MESH',                       # Wire: P0.13 / P0.14
        '6': 'GPS_TXD', '7': 'GPS_RXD_MCU', '8': 'GPS_PPS',     # Serial1 RX / TX, PPS: P0.15 / P0.16 / P0.17
        '9': 'MESH_API_RX', '10': 'MESH_API_TX',                # P0.19 / P0.20: serial module (PROTO) to the host
        '11': None,                                             # P0.21: buzzer PWM (not fitted)
        '12': None,                                             # P0.10: AQ_SET, driven high by the firmware
        '13': 'MESH_BTN_N',                                     # P0.09: user button (needs UICR NFCPINS = GPIO)
        '14': 'GND', '15': 'MESH_RF_BT', '16': 'GND',
        '17': 'MESH_RST_N', '18': 'MESH_SWDCLK', '19': 'MESH_SWDIO',
        '20': '+3V3_MESH', '21': '+3V3_MESH', '22': 'GND',
        '23': None, '24': None, '25': None,
        '26': 'MESH_3V3_EN',                                    # P1.02: WB_IO2 / 3V3_EN -> GPS power (with SW50)
        '27': 'MESH_LED_G', '28': 'MESH_LED_B',                 # P1.03 / P1.04, active high
        '29': None, '30': None, '31': None, '32': None, '33': None, '34': None,
        '35': 'GND', '36': 'GND', '37': 'MESH_RF_LORA', '38': 'GND',
        '39': None, '40': 'VBAT_ADC', '41': None, '42': 'GND',
        '43': None,                                             # VDD_NRF: open (RAK4631 practice)
        '44': 'MESH_VBAT_NRF',
    }
    return [
        P('U40', 'MMDVM_r30:RAK4630', 'RAK4630-9-SM-NI', rak, 'MMDVM_r30:RAK4630',
          {'MPN': 'RAK4630-9-SM-NI (RF pads)',
           'Note': 'flash the RAK4631 bootloader via SWD; set UICR REGOUT0 = 3.3 V and NFCPINS = GPIO'}),
        R('R60', '0R', 'VSYS', 'MESH_VBAT_NRF', Note='RAK4631: VBAT -> VBAT_NRF'),
        C('C70', '10u', 'MESH_VBAT_NRF', 'GND', FP_C0603), C('C71', '100n', 'MESH_VBAT_NRF', 'GND'),
        C('C72', '10u', '+3V3_MESH', 'GND', FP_C0603), C('C73', '100n', '+3V3_MESH', 'GND'),
        R('R61', '10k', 'MESH_RST_N', '+3V3_MESH'), C('C74', '100n', 'MESH_RST_N', 'GND'),
        P('SW40', 'Switch:SW_Push', 'MESH RESET', {'1': 'MESH_RST_N', '2': 'GND'},
          'Button_Switch_SMD:SW_SPST_B3U-1000P', {'MPN': 'B3U-1000P'}),
        P('SW41', 'Switch:SW_Push', 'MESH BTN', {'1': 'MESH_BTN_N', '2': 'GND'},
          'Button_Switch_SMD:SW_SPST_B3U-1000P', {'MPN': 'B3U-1000P', 'Note': 'bench button, parallel to the front panel'}),
        R('R62', '100k', 'MESH_BTN_N', '+3V3_MESH'),
        R('R63', '1k', 'GPS_RXD_MCU', 'GPS_RXD', Note='GPS may be unpowered: limit back-drive'),
        R('R64', '1M', 'CELL+', 'VBAT_ADC', Note='RAK19007 divider; ADC_MULTIPLIER 1.73; no capacitor'),
        R('R65', '1.5M', 'VBAT_ADC', 'GND'),
        R('R66', '4k7', 'SDA_MESH', '+3V3_MESH'), R('R67', '4k7', 'SCL_MESH', '+3V3_MESH'),
        LED('D40', 'green', 'GND', 'D40_A', 'APHHS1005LCGCK'), R('R68', '1k', 'MESH_LED_G', 'D40_A'),
        P('J40', 'Connector:Conn_Coaxial', 'LoRa 920 U.FL', {'1': 'MESH_RF_LORA', '2': 'GND'}, FP_UFL,
          {'MPN': 'Hirose U.FL-R-SMT-1(10)', 'Note': 'pigtail to the top-wall SMA; 50 Ohm CPWG to pad 37'}),
        P('J41', 'Connector:Conn_Coaxial', 'BLE U.FL', {'1': 'MESH_RF_BT', '2': 'GND'}, FP_UFL,
          {'MPN': 'Hirose U.FL-R-SMT-1(10)', 'Note': '2.4 GHz FPC antenna in the top plenum'}),
        P('J42', 'Connector_Generic:Conn_02x05_Odd_Even', 'MESH SWD', {
            '1': '+3V3_MESH', '2': 'MESH_SWDIO', '3': 'GND', '4': 'MESH_SWDCLK', '5': 'GND', '6': None, '7': None,
            '8': None, '9': 'GND', '10': 'MESH_RST_N'},
          'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD',
          {'Note': 'Cortex-M 10-pin SWD, SMT (sits above a cell holder: no through-hole pins)'}),
        P('J43', 'Connector_Generic:Conn_01x04', 'MESH USB', {'1': 'MESH_VBUS', '2': 'MESH_USB_DM',
                                                              '3': 'MESH_USB_DP', '4': 'GND'},
          'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
          {'Note': 'internal: bootloader / UF2 (OTA over BLE also possible)'}),
        P('J44', 'Connector_Generic:Conn_01x06', 'FRONT PANEL', {'1': '+3V3_MESH', '2': 'GND', '3': 'SDA_MESH',
                                                                 '4': 'SCL_MESH', '5': 'MESH_BTN_N',
                                                                 '6': 'MESH_LED_B'},
          'Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal',
          {'Note': 'front panel: Heltec 1.3in SH1106 OLED (0x3C), MESH button, blue LED'}),
    ]


# ============================================================================== GPS
def gps():
    return [
        P('U50', 'RF_GPS:MAX-M10S', 'MAX-M10S', {
            '1': 'GND', '2': 'GPS_TXD', '3': 'GPS_RXD', '4': 'GPS_PPS', '5': None, '6': 'GPS_VBCKP',
            '7': '+3V3_GPS', '8': '+3V3_GPS', '9': None, '10': 'GND', '11': 'GPS_RF', '12': 'GND', '13': None,
            '14': 'GPS_VCC_RF', '15': None, '16': None, '17': None, '18': 'GPS_SAFEBOOT_N'},
          'RF_GPS:ublox_MAX', {'MPN': 'MAX-M10S-00B', 'Note': 'VIO_SEL open = 3.3 V I/O; UART 9600'}),
        P('U51', 'Power_Management:TPS22919DCK', 'TPS22919', {'1': '+3V3_MESH', '2': 'GND', '3': 'GPS_ON',
                                                              '4': None, '5': 'GPS_QOD', '6': '+3V3_GPS'},
          'Package_TO_SOT_SMD:SOT-363_SC-70-6', {'MPN': 'TPS22919DCKR', 'Note': 'Ron ~90 mOhm (< 0.2 Ohm rule)'}),
        R('R73', '100R', 'GPS_QOD', '+3V3_GPS', Note='quick output discharge'),
        C('C80', '1u', '+3V3_MESH', 'GND'), C('C81', '10u', '+3V3_GPS', 'GND', FP_C0603),
        C('C82', '100n', '+3V3_GPS', 'GND'),
        # GPS power = slide switch AND RAK P1.02 (3V3_EN): SW50 common -> GPS_ON
        P('SW50', 'Switch:SW_SPDT', 'GPS ON/OFF', {'1': 'MESH_3V3_EN', '2': 'GPS_ON', '3': 'GND'},
          'MMDVM_r30:SW_SPDT_PCM12_EdgeMount', {'MPN': 'C&K PCM12SMTR', 'Note': 'side-actuated slide switch'}),
        R('R70', '100k', 'GPS_ON', 'GND'),
        P('D50', 'Device:D_Schottky', 'BAT54', {'1': 'GPS_VBCKP', '2': '+3V3_MESH'}, 'Diode_SMD:D_SOD-323',
          {'MPN': 'BAT54HT1G', 'Note': 'backup supply keeps ephemeris while the GPS is switched off'}),
        C('C83', '1u', 'GPS_VBCKP', 'GND'),
        # active antenna bias (MAX-M10S integration manual fig. 37)
        R('R71', '10R', 'GPS_VCC_RF', 'GPS_ANT_BIAS', 'Resistor_SMD:R_0603_1608Metric', Note='0.25 W, current limit'),
        C('C84', '10n', 'GPS_ANT_BIAS', 'GND'),
        P('L50', 'Device:L', '27nH', {'1': 'GPS_ANT_BIAS', '2': 'GPS_RF'}, 'Inductor_SMD:L_0402_1005Metric',
          {'Note': 'LQW15AN27NG80D (680 mA); check impedance at L1 (~270 Ohm for 27 nH)'}),
        P('J50', 'Connector:Conn_Coaxial', 'GPS U.FL', {'1': 'GPS_RF', '2': 'GND'}, FP_UFL,
          {'MPN': 'Hirose U.FL-R-SMT-1(10)', 'Note': 'pigtail to the top-wall SMA, active antenna'}),
        P('TP50', 'Connector:TestPoint', 'SAFEBOOT', {'1': 'GPS_SAFEBOOT_N'}, 'TestPoint:TestPoint_Pad_D1.0mm',
          in_bom=False),
        LED('D51', 'green', 'GND', 'D51_A', 'APHHS1005LCGCK'), R('R72', '2k2', '+3V3_GPS', 'D51_A'),
    ]


# ============================================================================== power
def power():
    p = [
        # ---- USB-C input, PD sink (9 V via CFG1..3 = GND), TVS
        P('J100', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C (charge)', {
            'A1': 'GND', 'B1': 'GND', 'A12': 'GND', 'B12': 'GND', 'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS',
            'B9': 'VBUS', 'A5': 'USB_CC1', 'B5': 'USB_CC2', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DM',
            'B7': 'USB_DM', 'A8': None, 'B8': None, 'SH': 'GND'},
          'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal', {'MPN': 'GCT USB4105-GF-A'}),
        P('D100', 'Device:D_TVS', 'SMAJ15CA', {'1': 'VBUS', '2': 'GND'}, 'Diode_SMD:D_SMA', {'MPN': 'SMAJ15CA'}),
        P('U100', 'Interface_USB:CH224K', 'CH224A', {'1': 'CH224_VDD', '2': 'GND', '3': 'GND', '4': 'USB_DP',
                                                     '5': 'USB_DM', '6': 'USB_CC2', '7': 'USB_CC1',
                                                     '8': 'CH224_VBUS', '9': 'GND', '10': None, '11': 'GND'},
          'Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm',
          {'Note': 'CH224A (CH224K out of stock): CFG1/2/3 = 0/0/0 -> 9 V; pin 1 VHV and pin 8 VBUS direct to VBUS'}),
        R('R100', '0R', 'VBUS', 'CH224_VDD', 'Resistor_SMD:R_0805_2012Metric', Note='CH224A: 0R (CH224K: 1k VDD feed)'),
        C('C100', '1u', 'CH224_VDD', 'GND'), R('R101', '0R', 'VBUS', 'CH224_VBUS', Note='CH224A: 0R (CH224K: 10k)'),
        C('C101', '10u', 'VBUS', 'GND', FP_C0805, Note='25 V'),
        # ---- charger with NVDC power path
        P('U101', 'Battery_Management:BQ25895RTW', 'BQ25895', {
            '1': 'VBUS', '2': 'BQ_DPDM', '3': 'BQ_DPDM', '4': 'BQ_STAT', '5': 'SCL_AON', '6': 'SDA_AON',
            '7': 'PWR_INT_N', '8': 'GND', '9': 'GND', '10': 'BQ_ILIM', '11': 'BQ_TS', '12': 'BQ_QON',
            '13': 'CELL+', '14': 'CELL+', '15': 'VSYS', '16': 'VSYS', '17': 'GND', '18': 'GND', '19': 'BQ_SW',
            '20': 'BQ_SW', '21': 'BQ_BTST', '22': 'REGN', '23': 'BQ_PMID', '24': None, '25': 'GND'},
          'Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm_ThermalVias',
          {'MPN': 'BQ25895RTWR', 'Note': 'D+/D- shorted = DCP (3.25 A input limit), I2C 0x6A'}),
        C('C102', '1u', 'VBUS', 'GND', FP_C0603, Note='25 V'),
        C('C103', '10u', 'BQ_PMID', 'GND', FP_C0805, Note='25 V'), C('C104', '10u', 'BQ_PMID', 'GND', FP_C0805),
        C('C105', '47n', 'BQ_BTST', 'BQ_SW'), C('C106', '4u7', 'REGN', 'GND', FP_C0603),
        P('L100', 'Device:L', '1uH', {'1': 'BQ_SW', '2': 'VSYS'}, 'Inductor_SMD:L_Wuerth_HCI-5040',
          {'MPN': 'Wurth 7443340100 (1 uH, >7 A)'}),
        C('C107', '22u', 'VSYS', 'GND', FP_C0805), C('C108', '22u', 'VSYS', 'GND', FP_C0805),
        C('C109', '10u', 'CELL+', 'GND', FP_C0805), C('C110', '10u', 'CELL+', 'GND', FP_C0805),
        R('R102', '110R', 'BQ_ILIM', 'GND', Note='ILIM = 355/R -> 3.2 A'),
        R('R103', '5k23', 'REGN', 'BQ_TS', Note='JEITA network for a 103AT NTC'),
        R('R104', '30k1', 'BQ_TS', 'GND'),
        P('TH100', 'Device:Thermistor_NTC', '10k 103AT', {'1': 'BQ_TS', '2': 'GND'},
          'Resistor_SMD:R_0603_1608Metric', {'Note2': 'Murata NCU18XH103F60RB (successor of the NRND NCP18XH103F03RB)',
                                             'Note': 'place between the cells'}),
        R('R105', '2k2', 'VSYS', 'STAT_LED_A'), LED('D101', 'orange', 'BQ_STAT', 'STAT_LED_A', 'APHHS1005SECK'),
        P('D102', 'Device:D_Schottky', 'BAT54', {'1': 'PWR_BTN_N', '2': 'BQ_QON'}, 'Diode_SMD:D_SOD-323',
          {'MPN': 'BAT54HT1G', 'Note': 'power button also wakes the charger from ship mode'}),
        R('R106', '10k', 'PWR_INT_N', '+3V3_MESH'),
        # ---- 4 x 18650 in parallel, per-cell fuse, low-side protection
    ]
    for i in range(4):
        p.append(P('BT%d' % (100 + i), 'Device:Battery_Cell', '18650', {'1': 'CELL%d+' % (i + 1), '2': 'CELL-'},
                   'Battery:BatteryHolder_Keystone_1042_1x18650',
                   {'MPN': 'Keystone 1042P (polarized holder); unprotected flat-top cell'}))
        p.append(P('F%d' % (100 + i), 'Device:Fuse', '7A', {'1': 'CELL%d+' % (i + 1), '2': 'CELL+'},
                   'Fuse:Fuse_Littelfuse-NANO2-451_453', {'MPN': 'Littelfuse 0451007.MRL',
                                                 'Note': 'opens if a cell is inserted reversed'}))
    p += [
        P('U102', 'Battery_Management:BQ297xy', 'BQ29707', {'1': None, '2': 'PROT_COUT', '3': 'PROT_DOUT',
                                                            '4': 'CELL-', '5': 'PROT_BAT', '6': 'PROT_VM'},
          'Package_SON:WSON-6_1.5x1.5mm_P0.5mm',
          {'Note': 'BQ29707: OV 4.28 V, UV 2.80 V, OCC -150 mV, OCD +200 mV (data sheet SLUSBU9I table 4); BQ29728 (-60 / +100 mV) would trip near the 12 V boost full-load battery current'}),
        R('R107', '330R', 'CELL+', 'PROT_BAT'), C('C111', '100n', 'PROT_BAT', 'CELL-'),
        R('R108', '2k2', 'GND', 'PROT_VM'),
        # The gates are driven from the cell (2.8 .. 4.2 V). CSD17577Q3A is only specified from 4.5 V (typical
        # 13 mohm at 3.0 V, off the curve below 2.85 V); CSD16340Q3 has the same SON 3.3 x 3.3 pinout and is
        # guaranteed at 2.5 V: 7.8 mohm max (TI SLPS247). 25 V, gate +10 / -8 V: enough on one cell.
        P('Q100', 'Transistor_FET:CSD17577Q3A', 'CSD16340Q3', {'1': 'CELL-', '2': 'CELL-', '3': 'CELL-',
                                                               '4': 'PROT_DGATE', '5': 'PROT_MID'}, FP_NFET,
          {'MPN': 'CSD16340Q3', 'Note': 'discharge FET; Rds(on) 7.8 mohm max at VGS 2.5 V'}),
        P('Q101', 'Transistor_FET:CSD17577Q3A', 'CSD16340Q3', {'1': 'GND', '2': 'GND', '3': 'GND',
                                                               '4': 'PROT_CGATE', '5': 'PROT_MID'}, FP_NFET,
          {'MPN': 'CSD16340Q3', 'Note': 'charge FET; Rds(on) 7.8 mohm max at VGS 2.5 V'}),
        # ---- battery master switch: a DPDT slide switch in the two gate lines of the protection FETs.
        # ON: gates follow the BQ29707. OFF: each gate is tied to its own source, both FETs are off and the
        # pack is isolated in both directions (no discharge, no charging) with no extra standby current.
        # Wired by terminal position, not by pole numbering: the two terminals at one end (1, 6) are the ON
        # throws, the two at the other end (3, 4) the OFF throws, 2 and 5 are the commons.
        P('SW101', 'Switch:SW_DPDT_x2', 'BATTERY ON/OFF',
          {'1': 'PROT_DOUT', '2': 'PROT_DGATE', '3': 'CELL-', '4': 'GND', '5': 'PROT_CGATE', '6': 'PROT_COUT'},
          'Button_Switch_THT:SW_CK_JS202011AQN_DPDT_Angled',
          {'MPN': 'C&K JS202011AQN', 'Note': 'ON = lever towards the pad 1 / 6 end (C&K drawing: the lever '
                                             'closes the terminals at its own end)'}),
        R('R130', '1M', 'PROT_DGATE', 'CELL-', Note='gate defined while the switch travels'),
        R('R131', '1M', 'PROT_CGATE', 'GND', Note='gate defined while the switch travels'),
        # ---- fuel gauge
        P('U103', 'MMDVM_r30:MAX17048', 'MAX17048', {'1': 'GND', '2': 'CELL+', '3': 'CELL+', '4': 'GND',
                                                     '5': 'PWR_INT_N', '6': 'GND', '7': 'SCL_AON', '8': 'SDA_AON',
                                                     '9': 'GND'},
          'Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.9x1.3mm',
          {'MPN': 'MAX17048G+T10', 'Note': 'I2C 0x36; pinout checked against the data sheet; EP land (90-0065) not checked'}),
        C('C112', '100n', 'CELL+', 'GND'),
        # ---- 12 V boost for the host (TPS61178, load disconnect P-FET)
        P('U104', 'MMDVM_r30:TPS61178', 'TPS61178', {
            '1': 'B12_FREQ', '2': 'GND', '3': 'B12_ILIM', '4': 'B12_COMP', '5': 'B12_FB', '6': 'GND',
            '7': 'B12_SW', '8': 'B12_VOUT', '9': 'B12_DISDRV', '10': 'B12_VCC', '11': 'HOST_PWR_EN',
            '12': 'VSYS', '13': 'B12_BST'},
          'MMDVM_r30:TPS61178_RNW', {'MPN': 'TPS61178RNWR'}),
        C('C113', '22u', 'VSYS', 'GND', FP_C0805), C('C114', '22u', 'VSYS', 'GND', FP_C0805),
        P('L101', 'Device:L', '1.8uH', {'1': 'VSYS', '2': 'B12_SW'}, 'Inductor_SMD:L_Wuerth_HCI-1050',
          {'MPN': 'Wurth 744325180 (1.8 uH, 18 A sat, 3.5 mOhm)'}),
        C('C115', '100n', 'B12_BST', 'B12_SW'), C('C116', '4u7', 'B12_VCC', 'GND', FP_C0603),
        R('R109', '348k', 'B12_FREQ', 'GND', Note='~500 kHz (TI example)'),
        R('R110', '75k', 'B12_ILIM', 'GND', Note='745/R -> 9.9 A typ'),
        R('R111', '15k', 'B12_COMP', 'B12_CC'), C('C117', '6n8', 'B12_CC', 'GND'), C('C118', '10p', 'B12_COMP', 'GND'),
        R('R112', '732k', '+12V_BOOST', 'B12_FB', Note='12.08 V with 80.6k'), R('R113', '80.6k', 'B12_FB', 'GND'),
        C('C119', '10u', 'B12_VOUT', 'GND', FP_C1206, Note='25 V'), C('C120', '10u', 'B12_VOUT', 'GND', FP_C1206),
        P('Q102', 'MMDVM_r30:PMOS_SON8', 'CSD25404Q3', {'1': 'B12_VOUT', '2': 'B12_VOUT', '3': 'B12_VOUT',
                                                        '4': 'B12_DISDRV', '5': '+12V_BOOST'},
          'Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET', {'MPN': 'CSD25404Q3', 'Note': 'load disconnect'}),
        R('R114', '150k', 'B12_DISDRV', 'B12_VOUT'), C('C121', '22n', 'B12_DISDRV', 'B12_VOUT'),
        C('C122', '22u', '+12V_BOOST', 'GND', FP_C1206, Note='25 V'),
        C('C123', '22u', '+12V_BOOST', 'GND', FP_C1206), C('C124', '22u', '+12V_BOOST', 'GND', FP_C1206),
        # ---- 12 V current monitor + ideal diode into SYS_DCIN
        R('R115', '10m', '+12V_BOOST', '+12V_SENSE', 'Resistor_SMD:R_1206_3216Metric', Note='shunt 1 %'),
        P('U105', 'Sensor_Energy:INA226', 'INA226', {'1': 'GND', '2': 'GND', '3': None, '4': 'SDA_AON',
                                                     '5': 'SCL_AON', '6': '+3V3_MESH', '7': 'GND',
                                                     '8': '+12V_SENSE', '9': '+12V_SENSE', '10': '+12V_BOOST'},
          'Package_SO:TSSOP-10_3x3mm_P0.5mm', {'MPN': 'INA226AIDGSR', 'Note': 'I2C 0x40, measures host power'}),
        C('C125', '100n', '+3V3_MESH', 'GND'),
        P('U106', 'Power_Management:LM74700', 'LM74700', {'1': 'IDEAL_VCAP', '2': 'GND', '3': '+12V_SENSE',
                                                          '4': 'SYS_DCIN', '5': 'IDEAL_GATE', '6': '+12V_SENSE'},
          'Package_TO_SOT_SMD:SOT-23-6', {'MPN': 'LM74700QDBVRQ1', 'Note': 'blocks back-feed from the host DC jack'}),
        C('C126', '100n', 'IDEAL_VCAP', '+12V_SENSE'),
        P('Q103', 'Transistor_FET:CSD17577Q3A', 'CSD17577Q3A', {'1': '+12V_SENSE', '2': '+12V_SENSE',
                                                                '3': '+12V_SENSE', '4': 'IDEAL_GATE',
                                                                '5': 'SYS_DCIN'}, FP_NFET,
          {'Note': 'ideal-diode FET'}),
        C('C127', '10u', 'SYS_DCIN', 'GND', FP_C1206, Note='25 V'),
        # ---- 5 V (display, fan)
        P('U107', 'Converter_DCDC:TPS61022', 'TPS61022', {'1': 'GND', '2': 'B5_SW', '3': '+5V', '4': 'B5_FB',
                                                          '5': 'HOST_PWR_EN', '6': 'VSYS', '7': 'VSYS'},
          'Package_DFN_QFN:Texas_RWU0007A_VQFN-7_2x2mm_P0.5mm', {'MPN': 'TPS61022RWUR', 'Note': 'MODE high = FPWM'}),
        P('L102', 'Device:L', '1uH', {'1': 'VSYS', '2': 'B5_SW'}, 'Inductor_SMD:L_Coilcraft_XAL4040-XXX',
          {'MPN': 'Coilcraft XAL4040-102 (1 uH)'}),
        R('R116', '732k', '+5V', 'B5_FB', Note='check VREF (0.6 V assumed)'), R('R117', '100k', 'B5_FB', 'GND'),
        C('C128', '10u', 'VSYS', 'GND', FP_C0805), C('C129', '22u', '+5V', 'GND', FP_C0805),
        C('C130', '22u', '+5V', 'GND', FP_C0805),
        # ---- 3.5 V buck-boost (always on) -> LDOs
        P('U108', 'Regulator_Switching:TPS63030DSK', 'TPS63030', {
            '1': '+3V5', '2': 'BB_L2', '3': 'GND', '4': 'BB_L1', '5': 'VSYS', '6': 'VSYS', '7': 'VSYS',
            '8': 'BB_VINA', '9': 'GND', '10': 'BB_FB', '11': 'GND'},
          'Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm', {'MPN': 'TPS63030DSKR', 'Note': 'PS/SYNC high = FPWM'}),
        R('R118', '100R', 'VSYS', 'BB_VINA'), C('C131', '100n', 'BB_VINA', 'GND'),
        P('L103', 'Device:L', '1.5uH', {'1': 'BB_L1', '2': 'BB_L2'}, 'Inductor_SMD:L_Coilcraft_XAL4040-XXX',
          {'MPN': 'Coilcraft XAL4040-152'}),
        R('R119', '604k', '+3V5', 'BB_FB', Note='3.52 V with VFB 0.5 V'), R('R120', '100k', 'BB_FB', 'GND'),
        C('C132', '10u', 'VSYS', 'GND', FP_C0805), C('C133', '10u', '+3V5', 'GND', FP_C0805),
        C('C134', '10u', '+3V5', 'GND', FP_C0805),
        P('U109', 'Regulator_Linear:TPS7A20xxxDBV', 'TPS7A2033', {'1': '+3V5', '2': 'GND', '3': '+3V5', '4': None,
                                                                  '5': '+3V3_MESH'},
          'Package_TO_SOT_SMD:SOT-23-5', {'MPN': 'TPS7A2033PDBVR', 'Note': 'always-on: RAK4630, GPS, I2C, sensors'}),
        C('C135', '1u', '+3V5', 'GND'), C('C136', '1u', '+3V3_MESH', 'GND'),
        P('U110', 'Regulator_Linear:TPS7A20xxxDBV', 'TPS7A2033', {'1': '+3V5', '2': 'GND', '3': 'HOST_PWR_EN',
                                                                  '4': None, '5': '+3V3'},
          'Package_TO_SOT_SMD:SOT-23-5', {'MPN': 'TPS7A2033PDBVR', 'Note': 'MMDVM (STM32 + 2x ADF7021), switched'}),
        C('C137', '1u', '+3V5', 'GND'), C('C138', '1u', '+3V3', 'GND'), C('C139', '10u', '+3V3', 'GND', FP_C0603),
        # ---- push-button power controller (host-side rails)
        P('U111', 'Power_Management:STM6601', 'STM6601CM2DDM6F', {
            '1': '+3V3_MESH', '2': '+3V3_MESH', '3': 'STM_VREF', '4': 'HOST_HOLD', '5': None, '6': 'PWR_BTN_N',
            '7': None, '8': None, '9': 'HOST_PWR_EN', '10': None, '11': 'BTN_INT_N', '12': 'GND'},
          'Package_DFN_QFN:TDFN-12_2x3mm_P0.5mm',
          {'Note': 'active-high push-pull EN. SR is held high, so there is no long-push forced off (it needs PB '
                   'and SR low plus a CSRD capacitor): a hung host is switched off with SW101. PS_HOLD must be '
                   'high when tON_BLANK ends: 5.6 s min (8.8 typ) on this CM2D variant, VTH+ 3.1 V; the CA2B '
                   'variant gives only 1.4 s. See C142 / R124 if the host is slower'}),
        # Start-up assist, not fitted: the 96Boards host raises +1V8 (-> HOST_HOLD) some time after power-on and
        # that time is not documented for the Bubblegum-96. If it is longer than tON_BLANK the controller drops
        # EN again. Fitting C142 (10 .. 22 uF), R124 (10k) and changing R43 to 1M holds PS_HOLD up from the EN
        # edge for roughly C142 x 1M (10 .. 20 s). Side effect: power-off after the host shuts down is delayed
        # by about the same time.
        C('C142', '10u', 'HOST_PWR_EN', 'HOLD_ASSIST', FP_C0603, dnp=True,
          Note='DNP: start-up assist, see U111'),
        R('R124', '10k', 'HOLD_ASSIST', 'HOST_HOLD', dnp=True, Note='DNP: start-up assist, see U111'),
        # DS (DocID15453 rev 14): the VREF pin needs its capacitor even when the reference is not used
        C('C141', '1u', 'STM_VREF', 'GND', Note='mandatory VREF capacitor'),
        C('C140', '100n', '+3V3_MESH', 'GND'), R('R121', '100k', 'PWR_BTN_N', '+3V3_MESH'),
        R('R122', '100k', 'HOST_PWR_EN', 'GND'), R('R123', '10k', 'BTN_INT_N', '+3V3_MESH'),
        P('SW100', 'Switch:SW_Push', 'POWER', {'1': 'PWR_BTN_N', '2': 'GND'},
          'MMDVM_r30:SW_Push_Alps_SKRTLAE010_NarrowPad1', {'MPN': 'Alps SKRTLAE010 (side push)'}),
        # ---- power flags (nets driven from connectors / cells)
        P('#FLG100', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'VBUS'}, in_bom=False),
        P('#FLG101', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'CELL+'}, in_bom=False),
        P('#FLG103', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'CELL-'}, in_bom=False),
        P('#FLG105', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'VSYS'}, in_bom=False),
        P('#FLG106', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+12V_SENSE'}, in_bom=False),
        P('#FLG107', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'SYS_DCIN'}, in_bom=False),
        P('#FLG108', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+12V_BOOST'}, in_bom=False),
        P('#FLG109', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'CH224_VDD'}, in_bom=False),
        P('#FLG110', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'MESH_VBAT_NRF'}, in_bom=False),
        P('#FLG111', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'MESH_VBUS'}, in_bom=False),
        P('#FLG112', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'GPS_VBCKP'}, in_bom=False),
    ]
    return p


# ============================================================================== Ethernet
# USB 2.0 from the Bubblegum-96 high-speed connector (pins 51/53 = downstream port 1 of its GL852G hub)
# into a LAN7500 (Hi-Speed USB to 10/100/1000 Ethernet, Linux driver smsc75xx) and a gigabit RJ45 with
# magnetics. The link is 1000BASE-T, the throughput is limited by USB 2.0.
# Connections follow the LAN7500 data sheet DS00001734B: table 2-8 (pins), tables 2-4..2-7, figure 6-2.
def ethernet():
    gnd_hs = (6, 12, 13, 18, 19, 24, 25, 30, 31, 37, 40, 43, 46, 49, 52, 55, 58)
    hs = {str(n): None for n in range(1, 61)}
    hs.update({str(n): 'GND' for n in gnd_hs})
    hs.update({'51': 'HS_USB_DP', '53': 'HS_USB_DM'})
    nc = (1, 2, 3, 4, 9, 10, 18, 21, 22, 25, 33, 34, 35, 38, 40)
    u = {str(n): None for n in nc}
    u.update({'5': 'ETH_XI', '6': 'ETH_XO',
              '7': '+3V3_ETH', '19': '+3V3_ETH', '24': '+3V3_ETH', '37': '+3V3_ETH',
              '8': '+1V2_ETH', '11': '+1V2_ETH', '20': '+1V2_ETH', '23': '+1V2_ETH', '30': '+1V2_ETH',
              '36': '+1V2_ETH',
              '26': 'ETH_EECLK', '27': 'ETH_EEDI', '28': 'ETH_EEDO', '29': 'ETH_EECS',
              '12': 'HS_USB_DM', '13': 'HS_USB_DP', '14': 'ETH_VBUS_DET', '15': 'ETH_VDD33A',
              '16': 'ETH_USBRBIAS', '17': 'ETH_VDD12USBPLL', '31': 'ETH_LED0_N', '32': 'ETH_LED1_N',
              '39': 'GND', '41': 'ETH_ETHRBIAS', '42': 'ETH_RST_N',
              '43': 'ETH_TR0N', '44': 'ETH_TR0P', '46': 'ETH_TR1N', '47': 'ETH_TR1P',
              '51': 'ETH_TR2N', '52': 'ETH_TR2P', '54': 'ETH_TR3N', '55': 'ETH_TR3P',
              '45': 'ETH_VDD12A', '48': 'ETH_VDD12A', '53': 'ETH_VDD12A', '56': 'ETH_VDD12A',
              '49': '+1V2_ETH', '50': 'ETH_VDD12PLL', '57': 'GND'})
    fb = lambda ref, a, b: P(ref, 'Device:FerriteBead', '120R@100MHz', {'1': a, '2': b},
                             'Inductor_SMD:L_0603_1608Metric', {'MPN': 'BLM18PG121SN1D', 'Note': '0.5 A min'})

    def buck(ref, lref, vout, sw, fbn, r_top, r_bot, refs):
        """TLV62569 (2 A, 0.6 V reference): Vout = 0.6 V x (1 + Rtop / Rbot); enabled by +1V8_HOST."""
        rt, rb, cin, co1, co2 = refs
        return [
            P(ref, 'Regulator_Switching:TLV62569DBV', 'TLV62569', {'1': '+1V8_HOST', '2': 'GND', '3': sw,
                                                                   '4': '+5V', '5': fbn},
              'Package_TO_SOT_SMD:SOT-23-5', {'MPN': 'TLV62569DBVR',
                                              'Note': 'EN from +1V8_HOST: VERIFY the EN high threshold'}),
            P(lref, 'Device:L', '2.2uH', {'1': sw, '2': vout}, 'Inductor_SMD:L_1008_2520Metric',
              {'MPN': 'Murata DFE252012F-2R2M', 'Note': 'Isat >= 1.5 A'}),
            R(rt, r_top, vout, fbn, Note='1 %'), R(rb, r_bot, fbn, 'GND', Note='1 %'),
            C(cin, '4u7', '+5V', 'GND', FP_C0603), C(co1, '10u', vout, 'GND', FP_C0603),
            C(co2, '10u', vout, 'GND', FP_C0603),
        ]
    p = [
        P('J10', 'Connector_Generic:Conn_02x30_Odd_Even', '96Boards HS', hs,
          'MMDVM_r30:AMPHENOL_61083-063402LF',
          {'MPN': 'Amphenol 61083-063402LF',
           'Note': 'bottom side; only USB (51/53) and GND are used. VERIFY mating height against the LS header'}),
    ]
    # supplies: on only while the host is up; both rails rise together (tpon <= 25 ms, figure 7-2)
    p += buck('U61', 'L64', '+3V3_ETH', 'ETH_SW33', 'ETH_FB33', '453k', '100k', ('R92', 'R93', 'C150', 'C151', 'C169'))
    p += buck('U62', 'L65', '+1V2_ETH', 'ETH_SW12', 'ETH_FB12', '100k', '100k', ('R94', 'R95', 'C170', 'C171', 'C172'))
    p += [
        P('U60', 'Interface_Ethernet:LAN7500-ABJZ', 'LAN7500', u,
          'Package_DFN_QFN:QFN-56-1EP_8x8mm_P0.5mm_EP5.9x5.9mm',
          {'MPN': 'LAN7500-ABZJ'}),
        # configuration EEPROM as in the Microchip reference design (93AA66A, 512 x 8 bit, 3-wire): holds the MAC
        # address and USB descriptors. A blank part is ignored (defaults apply); program it in circuit with
        # `ethtool -E`. Names follow the LAN7500 pins: EEDO drives the EEPROM DI, EEDI reads its DO.
        P('U64', 'Memory_EEPROM:93AAxxAT-xOT', '93LC66A', {'1': 'ETH_EEDI', '2': 'GND', '3': 'ETH_EEDO',
                                                            '4': 'ETH_EECLK', '5': 'ETH_EECS', '6': '+3V3_ETH'},
          'Package_TO_SOT_SMD:SOT-23-6', {'MPN': '93LC66AT-I/OT', 'Note': '8-bit organisation (A suffix) is required'}),
        C('C186', '100n', '+3V3_ETH', 'GND'),
        R('R78', '10k', 'ETH_EECS', 'GND', Note='EECS may float briefly at power-up (data sheet note)'),
        # decoupling per the Microchip schematic checklist (SC471232): 0.01 uF at every supply pin, a ferrite
        # bead with bulk capacitance on both sides for VDD33A, VDD12A, VDD12USBPLL and VDD12PLL, VDD12BIAS direct
        C('C152', '10n', '+3V3_ETH', 'GND'), C('C153', '10n', '+3V3_ETH', 'GND'),
        C('C154', '10n', '+3V3_ETH', 'GND'), C('C155', '10n', '+3V3_ETH', 'GND'),
        C('C156', '10n', '+1V2_ETH', 'GND'), C('C157', '10n', '+1V2_ETH', 'GND'),
        C('C158', '10n', '+1V2_ETH', 'GND'), C('C159', '10n', '+1V2_ETH', 'GND'),
        C('C161', '10n', '+1V2_ETH', 'GND'), C('C162', '10n', '+1V2_ETH', 'GND'),
        C('C177', '10n', '+1V2_ETH', 'GND', Note='VDD12BIAS'),
        C('C160', '4u7', '+1V2_ETH', 'GND', FP_C0603), C('C185', '4u7', '+3V3_ETH', 'GND', FP_C0603),
        fb('L60', '+3V3_ETH', 'ETH_VDD33A'), C('C163', '10n', 'ETH_VDD33A', 'GND'),
        C('C181', '4u7', 'ETH_VDD33A', 'GND', FP_C0603),
        fb('L61', '+1V2_ETH', 'ETH_VDD12USBPLL'), C('C179', '10n', 'ETH_VDD12USBPLL', 'GND'),
        C('C183', '4u7', 'ETH_VDD12USBPLL', 'GND', FP_C0603),
        fb('L62', '+1V2_ETH', 'ETH_VDD12A'),
        C('C173', '10n', 'ETH_VDD12A', 'GND'), C('C174', '10n', 'ETH_VDD12A', 'GND'),
        C('C175', '10n', 'ETH_VDD12A', 'GND'), C('C176', '10n', 'ETH_VDD12A', 'GND'),
        C('C182', '4u7', 'ETH_VDD12A', 'GND', FP_C0603),
        fb('L66', '+1V2_ETH', 'ETH_VDD12PLL'), C('C178', '10n', 'ETH_VDD12PLL', 'GND'),
        C('C184', '4u7', 'ETH_VDD12PLL', 'GND', FP_C0603),
        R('R80', '12k', 'ETH_USBRBIAS', 'GND', Note='1 %'), R('R81', '8k06', 'ETH_ETHRBIAS', 'GND', Note='1 %'),
        R('R82', '10k', 'ETH_VBUS_DET', '+3V3_ETH', Note='self powered, permanently attached'),
        # external power-on reset, as the checklist strongly recommends (the internal POR is RC based)
        P('U63', 'Power_Supervisor:LM809', 'LM809 2.93V', {'1': 'GND', '2': 'ETH_RST_N', '3': '+3V3_ETH'},
          'Package_TO_SOT_SMD:SOT-23', {'MPN': 'LM809M3X-2.93', 'Note': 'push-pull active-low reset, 240 ms'}),
        P('Y3', 'Device:Crystal_GND24', '25MHz', {'1': 'ETH_XI', '2': 'GND', '3': 'ETH_XO', '4': 'GND'},
          'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', {'MPN': '25 MHz 3225, 30 ppm or better, CL 18 pF'}),
        C('C165', '27p', 'ETH_XI', 'GND'), C('C166', '27p', 'ETH_XO', 'GND'),
        # 1000BASE-T: 49.9 ohm from each line and the transformer centre tap to the magnetics supply
        fb('L63', '+3V3_ETH', 'ETH_VMAG'), C('C167', '100n', 'ETH_VMAG', 'GND', Note='centre tap'),
        C('C180', '22n', 'ETH_VMAG', 'GND', Note='optional EMI capacitor, close to the jack'),
    ]
    for i, (r1, r2) in enumerate((('R85', 'R86'), ('R87', 'R88'), ('R96', 'R97'), ('R98', 'R99'))):
        p += [R(r1, '49R9', 'ETH_TR%dP' % i, 'ETH_VMAG', Note='1 %'), R(r2, '49R9', 'ETH_TR%dN' % i, 'ETH_VMAG', Note='1 %')]
    p += [
        P('J60', 'MMDVM_r30:RJ45_WE_7499111446', 'RJ45 10/100/1000',
          {'1': 'ETH_VMAG', '2': 'ETH_TR0P', '3': 'ETH_TR0N', '4': 'ETH_TR1P', '5': 'ETH_TR1N', '6': 'ETH_TR2P',
           '7': 'ETH_TR2N', '8': 'ETH_TR3P', '9': 'ETH_TR3N', '10': 'ETH_SHIELD', '11': 'ETH_LED_Y_A',
           '12': 'ETH_LED0_N', '13': 'ETH_LED_G_A', '14': 'ETH_LED1_N', 'SH': 'ETH_SHIELD'},
          'MMDVM_r30:RJ45_Wuerth_7499111446_EdgeMount',
          {'MPN': 'Wurth 7499111446',
           'Note': 'per Wurth spec rev 04 (2018-12-07): pin 1 = common centre tap, 2/3 4/5 6/7 8/9 = pairs (RJ45 1/2, 3/6, '
                   '4/5, 7/8), pin 10 = return of the internal 75 ohm / 1000 pF 2 kV termination (to chassis), '
                   'LEDs bicolour: green lights with 11 / 13 positive'}),
        R('R89', '330R', 'ETH_LED_Y_A', '+3V3_ETH'), R('R90', '330R', 'ETH_LED_G_A', '+3V3_ETH'),
        R('R91', '1M', 'ETH_SHIELD', 'GND', 'Resistor_SMD:R_1210_3225Metric',
          Note='chassis to digital ground link: 1210 so that 0R, a capacitor or a bead can be fitted at EMI test'),
        C('C168', '1n', 'ETH_SHIELD', 'GND', FP_C1206, Note='2 kV (1206: 2 kV parts are not stocked in 0805)'),
        P('#FLG120', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+3V3_ETH'}, in_bom=False),
        P('#FLG121', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+1V2_ETH'}, in_bom=False),
        P('#FLG122', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'ETH_VDD12A'}, in_bom=False),
        P('#FLG123', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'ETH_VDD12USBPLL'}, in_bom=False),
        P('#FLG124', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'ETH_VDD33A'}, in_bom=False),
        P('#FLG125', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'ETH_VDD12PLL'}, in_bom=False),
    ]
    return p
