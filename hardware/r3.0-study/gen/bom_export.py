"""Export the r3.0 study BOMs: grouped BOM (Mouser + LCSC) and a JLCPCB assembly BOM, csv + xlsx.

Run with any python that has openpyxl for the xlsx files (KiCad's python is enough for the csv files):
    python bom_export.py
Outputs: ../BOM.csv, ../BOM.xlsx, ../BOM_JLCPCB.csv and the same in ../front_panel/.
"""
import csv
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
KCLI = os.environ.get('KICAD_CLI', r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
PROJECTS = [(os.path.join(HERE, '..', 'mmdvm_mesh.kicad_sch'), os.path.join(HERE, '..')),
            (os.path.join(HERE, '..', 'front_panel', 'front_panel.kicad_sch'), os.path.join(HERE, '..', 'front_panel'))]
FIELDS = 'Reference,Value,Footprint,${QUANTITY},MFR,MPN,Mouser,Mouser_MPN,LCSC'


def export(sch, outdir):
    raw = os.path.join(outdir, 'BOM.csv')
    subprocess.run([KCLI, 'sch', 'export', 'bom', '--fields', FIELDS, '--labels',
                    'Reference,Value,Footprint,Qty,MFR,MPN,Mouser,Mouser MPN (if different),LCSC', '--group-by', 'Value,Footprint,MPN',
                    '--ref-delimiter', ',', '--ref-range-delimiter', '', '--exclude-dnp', '-o', raw, sch],
                   capture_output=True, check=True)
    rows = list(csv.DictReader(open(raw, encoding='utf-8')))
    jlc = os.path.join(outdir, 'BOM_JLCPCB.csv')
    with open(jlc, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for r in rows:
            w.writerow([r['Value'], r['Reference'], r['Footprint'].split(':')[-1], r['LCSC']])
    missing = [r['Reference'] for r in rows if not r['LCSC'] or not r['Mouser']]
    try:
        import openpyxl
        from openpyxl.styles import Font
        wb = openpyxl.Workbook()
        for title, path in (('BOM', raw), ('JLCPCB', jlc)):
            ws = wb.active if title == 'BOM' else wb.create_sheet(title)
            ws.title = title
            for i, row in enumerate(csv.reader(open(path, encoding='utf-8'))):
                ws.append(row)
                if i == 0:
                    for c in ws[1]:
                        c.font = Font(bold=True)
            ws.freeze_panes = 'A2'
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(len(str(c.value or '')) for c in col) + 2)
        wb.save(os.path.join(outdir, 'BOM.xlsx'))
    except ImportError:
        print('openpyxl not available: xlsx skipped')
    print(os.path.normpath(outdir), 'lines', len(rows), 'parts', sum(int(r['Qty']) for r in rows),
          '| lines missing Mouser or LCSC:', len(missing))
    return missing


if __name__ == '__main__':
    for sch, out in PROJECTS:
        export(os.path.normpath(sch), os.path.normpath(out))
