#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v4bisect.py — v4 解析二分变体
V1: unishare 头(GPDFileName/ModelName/MasterUnits/IsXPSDriver) + LJ2655DN 的 feature 段
V2: LJ2655DN 原文只去掉 *Include MSXPSINC.GPD(改内嵌 IsXPSDriver)
"""
import re, os

USH = r"C:\Windows\System32\spool\drivers\x64\3\unishare.gpd.ds.bak"
if not os.path.exists(USH):
    USH = r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak"
SRC = r"E:\Deepseek\lj2400woa\driver\LJ2655DN.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\v4b"

os.makedirs(OUT, exist_ok=True)

def read_gpd(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    return b.decode('utf-8-sig', errors='replace')

ush = read_gpd(USH)
src = read_gpd(SRC)

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

# V1: unishare 原文 + 我们的全部 feature 段与命令段(追加, 去重 unishare 同名)
v1 = ush
for name in ('Orientation', 'InputBin', 'MediaType', 'Resolution', 'PaperSize', 'Duplex', 'TonerSave', 'Sleep', 'ColorMode', 'Halftone'):
    blk = feat_block(src, name)
    if not blk:
        continue
    old = feat_block(v1, name)
    if old:
        v1 = v1.replace(old, blk)
    else:
        v1 = v1.rstrip() + '\n\n' + blk + '\n'
# 我们的约束行(Constraints root-level)
cons = re.findall(r'^\*UIConstraints:.*$', src, re.M)
if cons:
    v1 = v1.rstrip() + '\n' + '\n'.join(cons) + '\n'

# V2: LJ2655DN 原文去 MSXPSINC Include 改内嵌
v2 = src.replace('*Include:        "MSXPSINC.GPD"\n', '*IsXPSDriver?:    TRUE\n')
assert 'MSXPSINC' not in v2

open(os.path.join(OUT, "V1_ushead.gpd"), "wb").write(v1.encode("utf-16"))
open(os.path.join(OUT, "V2_noxpsinc.gpd"), "wb").write(v2.encode("utf-16"))
print("OK V1/V2", len(v1), len(v2))
