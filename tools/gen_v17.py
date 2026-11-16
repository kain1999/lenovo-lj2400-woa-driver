#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v17.py — V17: unishare 基座 + 我们 Orientation 段但 rcNameID 宏全部换 *Name 字面
分岔: rcNameID 宏 = v4 PrintConfig 崩点?"""
import re, os

OUT = r"E:\Deepseek\lj2400woa\build\v4s"

def read_gpd(p):
    b = open(p, 'rb').read()
    return b.decode('utf-16') if b[:2] == b'\xff\xfe' else b.decode('utf-8-sig', errors='replace')

ush = read_gpd(r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak")
s = read_gpd(os.path.join(OUT, 'S_Orientation.gpd'))

def feat_block(t, name):
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(name), t)
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

blk = feat_block(s, 'Orientation')
blk2 = blk.replace('*rcNameID: =ORIENTATION_DISPLAY', '*Name: "Orientation"')
blk2 = blk2.replace('*rcNameID: =PORTRAIT_DISPLAY', '*Name: "Portrait"')
blk2 = blk2.replace('*rcNameID: =LANDSCAPE_DISPLAY', '*Name: "Landscape"')

v17 = ush.replace(feat_block(ush, 'Orientation'), blk2)
open(os.path.join(OUT, 'V17_orien_literal.gpd'), 'wb').write(v17.encode('utf-16'))

# 统计我们 LJ2655DN.gpd 的宏使用规模
src = read_gpd(r"E:\Deepseek\lj2400woa\driver\LJ2655DN.gpd")
macros = re.findall(r'=RCID_\d+|=[A-Z_]+_DISPLAY|=[A-Z_]+_NAME', src)
print('OK V17, LJ2655DN 宏引用总数:', len(macros), '种类:', sorted(set(macros))[:12])
