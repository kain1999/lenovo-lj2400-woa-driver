#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_allen.py — 全量静态 GPD 所有非 ASCII 显示名替换为占位英文名 (v3 ANSI 验证版)"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\allen"
os.makedirs(OUT, exist_ok=True)

t = open(SRC, encoding="utf-16").read()

mapping = {}
def repl(m):
    s = m.group(1)
    if all(ord(c) < 128 for c in s):
        return m.group(0)
    if s not in mapping:
        mapping[s] = "L%d" % (len(mapping) + 1)
    return '"%s"' % mapping[s]

t2 = re.sub(r'"([^"]*)"', repl, t)
# 引号外的裸中文(注释等)一并消毒为 '?'
t3 = ''.join(c if ord(c) < 128 else '?' for c in t2)
open(os.path.join(OUT, "A7_allen.gpd"), "w", encoding="ascii", newline="\r\n").write(t3)
print("OK A7, 非ASCII名映射:", mapping)
