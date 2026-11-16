#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect3.py — B10: 全量去 MSXPSINC Include 改内嵌; B11: unishare 原文+我们的纸型段"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
USH = r"C:\Windows\System32\spool\drivers\x64\3\unishare.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect3"
os.makedirs(OUT, exist_ok=True)

text = open(SRC, encoding="utf-16").read()
# B10: 去 *Include MSXPSINC.GPD, 改为内嵌 *IsXPSDriver?: TRUE(unishare 同款)
b10 = text.replace('*Include:        "MSXPSINC.GPD"\n', '*IsXPSDriver?:    TRUE\n')
assert 'MSXPSINC' not in b10, "MSXPSINC 引用未清干净"

# B11: unishare 原文 + 把 PaperSize 段换成我们的(22 固定纸型段, 无 CUSTOMSIZE)
ush = open(USH, encoding="utf-8").read()

def extract_feature(t, name):
    m = re.search(r'\*Feature:\s+%s\s*\{' % re.escape(name), t)
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

def replace_feature(t, name, new_block):
    m = re.search(r'\*Feature:\s+%s\s*\{' % re.escape(name), t)
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
    return t[:m.start()] + new_block + t[j + 1:]

paper_block = extract_feature(text, "PaperSize")
b11 = replace_feature(ush, "PaperSize", paper_block)

open(os.path.join(OUT, "B10_noxpsinc.gpd"), "wb").write(b10.encode("utf-16"))
open(os.path.join(OUT, "B11_usdpaper.gpd"), "wb").write(b11.encode("utf-16"))
print("OK B10/B11", len(b10), len(b11))
