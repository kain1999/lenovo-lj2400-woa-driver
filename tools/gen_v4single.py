#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v4single.py — unishare 原文 + 单 feature 段注入(去约束) × 9 变体定位 v4 PrintConfig 崩点"""
import re, os

USH = r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak"
SRC = r"E:\Deepseek\lj2400woa\driver\LJ2655DN.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\v4s"

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

def decon(t):
    return re.sub(r'\s*\*Constraints:.*\n', '\n', t)

CASES = ['Orientation', 'InputBin', 'MediaType', 'Resolution', 'PaperSize', 'Duplex', 'TonerSave', 'Sleep', 'ColorMode', 'Halftone']
for name in CASES:
    blk = feat_block(src, name)
    if not blk:
        print('skip', name)
        continue
    t = ush
    old = feat_block(t, name)
    blk2 = decon(blk)
    if old:
        t = t.replace(old, blk2)
    else:
        t = t.rstrip() + '\n\n' + blk2 + '\n'
    open(os.path.join(OUT, 'S_%s.gpd' % name), 'wb').write(t.encode('utf-16'))
    print('OK S_%s' % name, len(t))
