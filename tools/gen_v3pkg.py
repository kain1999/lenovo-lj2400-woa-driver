#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v3pkg.py — 实测 A: 自家未签名 v3 驱动包
P1: LJ2655DN.gpd = Y3b(渲染全验证: 240dpi+全feature+EOJ修复, ASCII 英文名)
P2: LJ2655DN.gpd 600dpi 版 = Y3b + 我们 Resolution 段替换(600dpi 栅格链验证用)
INF: v3 纯引用形态(无 CoreDriverSections, 无 CopyFiles unidrv 组件)
"""
import re, os

OUT = r"E:\Deepseek\lj2400woa\build\v3pkg"
os.makedirs(OUT, exist_ok=True)

def read_gpd(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    return b.decode('utf-8-sig', errors='replace')

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

y3b = read_gpd(r"E:\Deepseek\lj2400woa\build\inc8\Y3b_eoj.gpd")
src = read_gpd(r"E:\Deepseek\lj2400woa\driver\LJ2655DN.gpd")

# P1 = Y3b 原样
open(os.path.join(OUT, 'LJ2655DN.gpd'), 'w', encoding='ascii', newline='\r\n').write(y3b)

# P2 = Y3b + 我们 Resolution 段(去约束, 栅格链 300/600/HQ1200)
MAP = {
    '分辨率': 'Resolution',
}
def clean(block):
    def rm(m):
        s = m.group(1)
        for k, v in MAP.items():
            s = s.replace(k, v)
        return '"%s"' % s
    s = re.sub(r'"([^"]*)"', rm, block)
    return ''.join(c if ord(c) < 128 else '?' for c in s)

res = clean(feat_block(src, 'Resolution'))
res = re.sub(r'\s*\*Constraints:.*\n', '\n', res)

old = feat_block(y3b, 'Resolution')
p2 = y3b.replace(old, res)
open(os.path.join(OUT, 'LJ2655DN_600.gpd'), 'w', encoding='ascii', newline='\r\n').write(p2)
print('OK P1=%d P2=%d' % (len(y3b), len(p2)))
print('P2 Resolution options:', re.findall(r'\*Option:\s*(\w+)', res))
