"""Check every LCSC number of ../BOM.csv against the JLCPCB parts library (any python 3, needs network access).

For each BOM line: does the library part number match the MPN of the BOM, is it a basic or an extended part,
and how many are in the assembly stock. (The LCSC shop stock is a different figure: common basic parts show
0 there while JLCPCB holds millions.) Run it again on the day of the order.

Usage: python stock_check.py [boards] [BOM.csv]     (boards: how many boards the order is for, default 5;
       BOM.csv: another grouped BOM, e.g. ../front_panel/BOM.csv)
"""
import csv
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARDS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
URL = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'


def norm(s):
    return re.sub(r'[^A-Z0-9]', '', s.upper())


BOM = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'BOM.csv')
rows = list(csv.DictReader(open(BOM, encoding='utf-8-sig')))
bad = ext = 0
print('%-10s %-26s %-26s %-5s %8s %6s  %s' % ('LCSC', 'BOM MPN', 'library part', 'type', 'stock', 'need', 'refs'))
for r in rows:
    code = r['LCSC'].strip()
    refs = r['Reference']
    need = int(r['Qty']) * BOARDS
    if not code:
        print('%-10s %-26s %-26s %8s %6d  %s   <-- NO LCSC NUMBER' % ('-', r['MPN'][:26], '', '', need, refs[:40]))
        bad += 1
        continue
    try:
        req = urllib.request.Request(URL, data=json.dumps({'keyword': code, 'currentPage': 1, 'pageSize': 10}).encode(),
                                     headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
        hits = json.load(urllib.request.urlopen(req, timeout=30))['data']['componentPageInfo']['list'] or []
        d = ([h for h in hits if h.get('componentCode') == code] or [{}])[0]
    except Exception as e:                       # noqa: BLE001
        print('%-10s lookup failed: %s' % (code, e))
        bad += 1
        continue
    model, stock = d.get('componentModelEn') or '', d.get('stockCount')
    kind = {'base': 'basic', 'expand': 'ext'}.get(d.get('componentLibraryType'), '?')
    notes = []
    a, c = norm(r['MPN']), norm(model)
    if not model:
        notes.append('NOT IN THE LIBRARY')
    elif not (a == c or (len(c) > 5 and (a.startswith(c) or c.startswith(a)))):
        notes.append('PART NUMBER DIFFERS')
    if stock is None:
        notes.append('no stock figure')
    elif stock < need:
        notes.append('OUT OF STOCK' if stock == 0 else 'STOCK BELOW NEED')
    elif stock < 10 * need:
        notes.append('low stock')
    if notes:
        bad += 1
    ext += kind != 'basic'
    print('%-10s %-26s %-26s %-5s %8s %6d  %s%s' % (code, r['MPN'][:26], model[:26], kind, stock, need, refs[:40],
                                              ('   <-- ' + ', '.join(notes)) if notes else ''))
    time.sleep(0.15)
print('lines: %d (not basic: %d), lines to look at: %d (for %d boards)' % (len(rows), ext, bad, BOARDS))
