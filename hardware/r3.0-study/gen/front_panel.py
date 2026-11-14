"""Front-panel board of the r3.0 study: MESH button, notification LED, OLED cable header, cable to main J44.

The Heltec 1.3" SH1106 I2C module is screwed to the enclosure front plate and wired to J2 with a short
4-wire Dupont cable, so its exact header position and pin order do not constrain this board (the cable
is wired to the module's printed labels). Run with KiCad's python:  python front_panel.py   -> ../front_panel/front_panel.kicad_sch
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import kisch  # noqa: E402
from r30_parts import C, LED, P, R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'front_panel'))
PROJECT = 'front_panel'
POWER = {'GND', '+3V3_MESH'}


def parts():
    return [
        P('J1', 'Connector_Generic:Conn_01x06', 'TO MAIN J44', {'1': '+3V3_MESH', '2': 'GND', '3': 'SDA', '4': 'SCL',
                                                                 '5': 'BTN_N', '6': 'LED_B'},
          'Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal',
          {'MPN': 'JST SM06B-SRSS-TB', 'Note': '1:1 JST-SH cable to main-board J44'}),
        P('J2', 'Connector_Generic:Conn_01x04', 'OLED', {'1': 'GND', '2': '+3V3_MESH', '3': 'SCL', '4': 'SDA'},
          'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
          {'Note': 'Heltec 1.3in SH1106 I2C (0x3C) via 4-wire Dupont cable: match the module labels '
                   '(some modules swap VCC/GND)'}),
        C('C1', '10u', '+3V3_MESH', 'GND', 'Capacitor_SMD:C_0603_1608Metric'),
        C('C2', '100n', '+3V3_MESH', 'GND'),
        P('SW1', 'Switch:SW_Push', 'MESH', {'1': 'BTN_N', '2': 'GND'}, 'Button_Switch_THT:SW_PUSH_6mm_H8mm',
          {'MPN': '6x6 mm tact switch, 8 mm high', 'Note': 'actuator through the front plate'}),
        R('R1', '150R', 'LED_B', 'LED_A', Note='blue LED from nRF P1.04 (3.3 V); adjust for brightness'),
        LED('D1', 'blue', 'GND', 'LED_A', 'APT2012QBC/D'),
        P('H1', 'Mechanical:MountingHole', 'M2.5', {}, 'MountingHole:MountingHole_2.7mm_M2.5', in_bom=False),
        P('H2', 'Mechanical:MountingHole', 'M2.5', {}, 'MountingHole:MountingHole_2.7mm_M2.5', in_bom=False),
        P('#FLG1', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+3V3_MESH'}, in_bom=False),
        P('#FLG2', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'GND'}, in_bom=False),
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    root = str(uuid.uuid4())
    sh = kisch.Sheet('front_panel', 'front_panel.kicad_sch', 'r3.0 front panel (MESH button, LED, OLED)',
                     set(), POWER, PROJECT, root, None, cols_mm=380.0)
    pp = parts()
    for p in pp:
        if p['ref'] == 'D1':
            p['fp'] = 'LED_SMD:LED_0805_2012Metric'
        sh.add(p['ref'], p['lib'], p['value'], p['nets'], footprint=p['fp'], fields=p['fields'], dnp=p['dnp'],
               in_bom=p['in_bom'])
    path = os.path.join(OUT, PROJECT + '.kicad_sch')
    sh.write(path)
    pro = os.path.join(OUT, PROJECT + '.kicad_pro')
    if not os.path.exists(pro):
        json.dump({"meta": {"filename": PROJECT + ".kicad_pro", "version": 3}}, open(pro, 'w'))
    viol, bad, got = build.verify(path, [('front_panel', 'front_panel.kicad_sch', pp)])
    print('front panel schematic: NETDIFF', bad, '| ERC', len(viol))
    for p_, v in viol:
        print('  -', v['severity'], v['type'], [i['description'][:60] for i in v['items']][:2])
    return path


if __name__ == '__main__':
    main()
