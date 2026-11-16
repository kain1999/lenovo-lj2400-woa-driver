#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc4.py — A9 系列: Duplex/ColorMode 去 Constraints + MSXPSINC Include 单测"""
import re, os

INC3 = r"E:\Deepseek\lj2400woa\build\inc3"
OUT = r"E:\Deepseek\lj2400woa\build\inc4"
os.makedirs(OUT, exist_ok=True)

base = open(os.path.join(INC3, "A8a_media.gpd"), encoding="gbk").read()
dup = open(os.path.join(INC3, "A8c_duplex.gpd"), encoding="ascii").read()
col = open(os.path.join(INC3, "A8f_colormode.gpd"), encoding="ascii").read()

def drop_constraints_in_block(t, fkey):
    """在 *Feature: <fkey> 段内删 *Constraints 行"""
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(fkey), t)
    if not m:
        return t
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
    seg = t[m.start():j + 1]
    seg2 = re.sub(r'\s*\*Constraints:.*\n', '\n', seg)
    return t[:m.start()] + seg2 + t[j + 1:]

a9a = drop_constraints_in_block(dup, 'Duplex')
a9b = drop_constraints_in_block(col, 'ColorMode')
a9b = drop_constraints_in_block(a9b, 'Halftone')
a9e = base.replace('*Include:        "StdNames.gpd"', '*Include:        "StdNames.gpd"\n*Include:        "MSXPSINC.GPD"')

for n, body in (('A9a_dupnocon', a9a), ('A9b_colnocon', a9b), ('A9e_xpsinc', a9e)):
    open(os.path.join(OUT, n + '.gpd'), 'w', encoding='ascii', newline='\r\n').write(body)
    print('OK', n, len(body))
