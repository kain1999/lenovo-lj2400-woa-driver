#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v3pack.py — v3 全套包 27 型号并列生成
基准: build\v3pkg\LJ2655DN_600.gpd(Y3b 结构+600dpi Resolution+EOJ修复, 渲染验证内容)
形态: ASCII 无 BOM / LF 行尾 / 无 >0x7F 字节 / 显示名 "Lenovo <Model>"
per-model: GPDFileName/ModelName 替换; 能力矩阵删段(无Duplex删MyDuplex, 无Sleep删Sleep); 删 ResourceDLL 行(=RCID_ 引用为 0)
产物: E:\Deepseek\lj2400woa\v3pkg\{LJ2400V3.INF, <MODEL>.gpd ×27}
自检: build\v3_selfcheck.txt
"""
import json
import re
import os

BASE = r"E:\Deepseek\lj2400woa\build\v3pkg\LJ2655DN_600.gpd"
JSON = r"E:\Deepseek\lj2400lin\analysis\ppd_extract.json"
OUT = r"E:\Deepseek\lj2400woa\v3pkg"
SELF = r"E:\Deepseek\lj2400woa\build\v3_selfcheck.txt"

os.makedirs(OUT, exist_ok=True)

base = open(BASE, encoding='ascii').read().replace('\r\n', '\n')
models = json.load(open(JSON, encoding='utf-8'))
assert isinstance(models, list) and len(models) == 27

def feat_block(t, name):
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(name), t)
    if not m:
        return ''
    i = m.end() - 1
    depth = 0
    j = i
    while j < len(t):
        if t[j] == '{':
            depth += 1
        elif t[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    return t[m.start():j + 1]

def has_openui(m, key):
    for it in (m.get('OpenUI') or []):
        if isinstance(it, dict) and key in str(it.get('name', '')):
            return True
    return False

results = []
fails = []
for m in models:
    name = m['ModelName']            # "LJ2400 Pro"
    fn = name.replace(' ', '')       # LJ2400Pro
    t = base
    # 1. 删 ResourceDLL 行(0 处 =RCID_ 引用, 内建宏不依赖资源 DLL)
    t = re.sub(r'\*ResourceDLL:\s*"ok9ibres\.dll"\s*\n', '', t)
    # 2. 头部 per-model
    t = t.replace('*GPDFileName: "GENIBM9.GPD"', '*GPDFileName: "%s.gpd"' % fn)
    t = t.replace('*ModelName: "Generic IBM Graphics 9pin"', '*ModelName: "Lenovo %s"' % name)
    # 3. 能力矩阵删段
    if not has_openui(m, 'Duplex'):
        blk = feat_block(t, 'MyDuplex')
        if blk:
            t = t.replace(blk, '')
    if not (has_openui(m, 'Sleep') or m.get('Sleep_opts')):
        blk = feat_block(t, 'Sleep')
        if blk:
            t = t.replace(blk, '')
    # 4. LF 统一 + 清理连续空行
    t = re.sub(r'\n{3,}', '\n\n', t).rstrip() + '\n'
    # 5. 校验
    bad = [c for c in t if ord(c) > 0x7F]
    depth = 0
    mn = 0
    for c in t:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            mn = min(mn, depth)
    ok = (not bad) and depth == 0 and mn == 0
    if not ok:
        fails.append((fn, len(bad), depth, mn))
    open(os.path.join(OUT, fn + '.gpd'), 'w', encoding='ascii', newline='\n').write(t)
    results.append((fn, name, len(t), ok, has_openui(m, 'Duplex'), has_openui(m, 'Sleep') or bool(m.get('Sleep_opts'))))

# INF: 27 section 并列
sec = []
strings = []
sdf = []
for i, m in enumerate(models, 1):
    name = m['ModelName']
    fn = name.replace(' ', '')
    sec.append('%%Model.%d%% = %s.Install' % (i, fn))
    strings.append('Model.%d = "Lenovo %s"' % (i, name))
    sdf.append('%s.gpd=1' % fn)

inf = []
inf.append('[Version]')
inf.append('Signature="$Windows NT$"')
inf.append('Provider=%LENOVO%')
inf.append('ClassGUID={4D36E979-E325-11CE-BFC1-08002BE10318}')
inf.append('Class=Printer')
inf.append('DriverVer=11/16/2026,1.0.0.1')
inf.append('')
inf.append('[Manufacturer]')
inf.append('%LENOVO%=Lenovo, NTamd64')
inf.append('')
inf.append('[Lenovo.NTamd64]')
inf.extend(sec)
inf.append('')
for i, m in enumerate(models, 1):
    fn = m['ModelName'].replace(' ', '')
    inf.append('[%s.Install]' % fn)
    inf.append('DataFile=%s.gpd' % fn)
    inf.append('DriverFile=UNIDRV.DLL')
    inf.append('ConfigFile=UNIDRVUI.DLL')
    inf.append('HelpFile=UNIDRV.HLP')
    inf.append('DriverIsolation=2')
    inf.append('CopyFiles=@%s.gpd' % fn)
    inf.append('')
inf.append('[DestinationDirs]')
inf.append('DefaultDestDir=66000')
inf.append('')
inf.append('[SourceDisksNames]')
inf.append('1 = %Disk1%')
inf.append('')
inf.append('[SourceDisksFiles]')
inf.extend(sdf)
inf.append('')
inf.append('[Strings]')
inf.append('LENOVO="Lenovo"')
inf.append('Disk1="Lenovo LJ24/LJ26/M74/M76 v3 Driver Disk"')
inf.extend(strings)
inf_text = '\n'.join(inf) + '\n'
open(os.path.join(OUT, 'LJ2400V3.INF'), 'w', encoding='ascii', newline='\n').write(inf_text)

# ============ 自检 ============
lines = []
lines.append('v3 全套包自检 — %s' % __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
lines.append('')
npass = 0
nfail = 0
for fn, name, size, ok, dup, slp in results:
    p = os.path.join(OUT, fn + '.gpd')
    raw = open(p, 'rb').read()
    a1 = all(b <= 0x7F for b in raw)
    a2 = b'\r' not in raw
    a3 = not raw.startswith(b'\xff\xfe')
    t = raw.decode('ascii')
    depth = t.count('{') - t.count('}')
    a4 = depth == 0
    has_fn = ('*GPDFileName: "%s.gpd"' % fn) in t
    has_mn = ('*ModelName: "Lenovo %s"' % name) in t
    dup_ok = (('MyDuplex' in t) == dup)
    slp_ok = (('Feature: Sleep' in t) == slp)
    eoj = ('*Order: JOB_FINISH.1' in t)
    all_ok = all([a1, a2, a3, a4, has_fn, has_mn, dup_ok, slp_ok, eoj])
    if all_ok:
        npass += 1
    else:
        nfail += 1
    lines.append('[%s] %s  ascii=%s LF=%s noBOM=%s brace=%s gpdname=%s modelname=%s duplex=%s(%s) sleep=%s(%s) eojfix=%s'
                 % ('PASS' if all_ok else 'FAIL', fn, a1, a2, a3, a4, has_fn, has_mn, dup, dup_ok, slp, slp_ok, eoj))

inf_raw = open(os.path.join(OUT, 'LJ2400V3.INF'), 'rb').read()
inf_ok = all(b <= 0x7F for b in inf_raw)
sec_count = len(re.findall(r'^\[(\S+\.Install)\]', inf_raw.decode('ascii'), re.M))
map_ok = True
for m in models:
    fn = m['ModelName'].replace(' ', '')
    if ('DataFile=%s.gpd' % fn) not in inf_raw.decode('ascii'):
        map_ok = False
    if not os.path.exists(os.path.join(OUT, fn + '.gpd')):
        map_ok = False
if inf_ok and sec_count == 27 and map_ok:
    npass += 1
else:
    nfail += 1
lines.append('[%s] LJ2400V3.INF  ascii=%s sections=%d(需27) map27=%s' % ('PASS' if (inf_ok and sec_count == 27 and map_ok) else 'FAIL', inf_ok, sec_count, map_ok))
lines.append('')
lines.append('合计: %d/%d PASS' % (npass, npass + nfail))
lines.append('产物目录: %s (%d GPD + 1 INF)' % (OUT, len(results)))

open(SELF, 'w', encoding='utf-8-sig').write('\n'.join(lines) + '\n')
print('\n'.join(lines[-3:]))
if fails:
    print('FAILS:', fails)
