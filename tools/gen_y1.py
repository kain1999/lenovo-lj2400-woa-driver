#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_y1.py — Y1 = 原版 GENIBM9.GPD + PJL 三命令(CmdStartJob/StartDoc/EndJob)
增量端逼近: 从 CreateDC 成功的原版出发"""
import re, os

ORIG = r"E:\Deepseek\lj2400woa\build\GENIBM9.GPD.orig.bak"
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8"

orig = open(ORIG, encoding="utf-8").read()   # 备份来自 x64\3(printui 处理过), 先试 ASCII
if '\x00' in orig[:200]:
    orig = open(ORIG, encoding="utf-16").read()
full = open(FULL, encoding="utf-16").read()

def cmd_block(t, name):
    m = re.search(r'(\*Command:\s+%s\s*\{)' % re.escape(name), t)
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
    return t[m.start():j + 1:]

# 我们的三命令(ASCII 化)
trip = '\n'.join(filter(None, [cmd_block(full, 'CmdStartJob'), cmd_block(full, 'CmdStartDoc'), cmd_block(full, 'CmdEndJob')]))
trip = ''.join(c if ord(c) < 128 else '?' for c in trip)

y1 = orig.rstrip() + '\n\n' + trip + '\n'
open(os.path.join(OUT, "Y1_pjl.gpd"), "w", encoding="ascii", newline="\r\n").write(y1)
print("OK Y1", len(y1), "orig_enc_ok")
