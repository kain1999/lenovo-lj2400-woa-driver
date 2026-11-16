# -*- coding: utf-8 -*-
"""Inspect ppd_extract.json: dump per-model full fields to UTF-8 overview file."""
import json, sys

SRC = r'E:\Deepseek\lj2400lin\analysis\ppd_extract.json'
OUT = r'E:\Deepseek\lj2400woa\build\ppd_overview.txt'

d = json.load(open(SRC, encoding='utf-8'))
out = open(OUT, 'w', encoding='utf-8')

out.write('=== MODEL[0] FULL ===\n')
out.write(json.dumps(d[0], ensure_ascii=False, indent=1))
out.write('\n\n=== VARIANCE TABLE ===\n')
keys = set()
for m in d:
    keys.update(m.keys())
out.write('all keys: ' + ', '.join(sorted(keys)) + '\n\n')
for k in sorted(keys):
    vals = set(json.dumps(m.get(k), ensure_ascii=False) for m in d)
    if len(vals) == 1:
        out.write('[%s] IDENTICAL\n' % k)
    else:
        out.write('[%s] varies x%d\n' % (k, len(vals)))

out.write('\n=== PER MODEL SUMMARY ===\n')
for m in d:
    out.write('%s\n' % m['file'])
    out.write('  ModelName=%s Product=%s Type=%s\n' % (m['ModelName'], m.get('Product'), m.get('BrPrinterType')))
    out.write('  PageSize n=%d: %s\n' % (len(m['PageSize_opts']), m['PageSize_opts']))
    out.write('  Duplex=%s Default=%s\n' % (m.get('Duplex_opts'), m.get('DefaultDuplex')))
    out.write('  Sleep n=%d Toner n=%d\n' % (len(m.get('Sleep_opts', [])), len(m.get('toner_opts', []))))
    out.write('  UIConstraints n=%d:\n' % len(m.get('UIConstraints', [])))
    for c in m.get('UIConstraints', []):
        out.write('    %s\n' % c)
    out.write('  MaxMedia=%sx%s VarPS=%s BrCustom=%s\n' % (m.get('MaxMediaWidth'), m.get('MaxMediaHeight'),
                                                          m.get('VariablePaperSize'), m.get('BrCustomPaperSize')))
    out.write('  InputSlot=%s Def=%s\n' % (m.get('InputSlot_opts'), m.get('DefaultInputSlot')))
    out.write('  Media=%s Def=%s\n' % (m.get('BrMediaType_opts'), m.get('DefaultBrMediaType')))
    out.write('  Res=%s Def=%s\n\n' % (m.get('Resolution_opts'), m.get('DefaultResolution')))

# OpenUI 中文名与各选项翻译
out.write('=== OPENUITRANS PER MODEL ===\n')
for m in d:
    out.write('%s: %s\n' % (m['ModelName'], json.dumps(m.get('OpenUI'), ensure_ascii=False)))

out.close()
print('written', OUT)
