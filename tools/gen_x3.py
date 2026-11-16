#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_x3.py — X3 = X2 全去 Constraints（悬空引用假说验证）"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\inc8\X2_nopaper.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8\X3_nocon.gpd"

t = open(SRC, encoding="ascii").read()
t2 = re.sub(r'\s*\*Constraints:.*\n', '\n', t)
open(OUT, "w", encoding="ascii", newline="\r\n").write(t2)
print("OK X3", len(t2))
