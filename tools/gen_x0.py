#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_x0.py — X0 = X3 去掉 *IsXPSDriver?: TRUE（渲染层根因验证）"""
import os

SRC = r"E:\Deepseek\lj2400woa\build\inc8\X3_nocon.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8\X0_noxps.gpd"

t = open(SRC, encoding="ascii").read()
t2 = t.replace('*IsXPSDriver?:    TRUE\n', '').replace('*IsXPSDriver?: TRUE\n', '')
assert 'IsXPSDriver' not in t2, 'IsXPSDriver 未清干净'
open(OUT, "w", encoding="ascii", newline="\r\n").write(t2)
print("OK X0", len(t2))
