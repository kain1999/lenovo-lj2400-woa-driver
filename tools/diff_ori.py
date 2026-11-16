#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_ori.py — V14 Orientation 段 vs unishare 原段逐行对比"""
import re, difflib

def read_gpd(p):
    b = open(p, 'rb').read()
    return b.decode('utf-16') if b[:2] == b'\xff\xfe' else b.decode('utf-8-sig', errors='replace')

ush = read_gpd(r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak")
v14 = read_gpd(r"E:\Deepseek\lj2400woa\build\v4s\V14_orien_fullen.gpd")

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

a = feat_block(ush, 'Orientation').replace('\r\n', '\n').split('\n')
b = feat_block(v14, 'Orientation').replace('\r\n', '\n').split('\n')
print('=== unishare 原段 %d 行 ===' % len(a))
for l in a:
    print(repr(l))
print('=== V14 段 %d 行 ===' % len(b))
for l in b:
    print(repr(l))
print('=== unified diff ===')
for l in difflib.unified_diff(a, b, 'orig', 'v14', lineterm=''):
    print(l)
