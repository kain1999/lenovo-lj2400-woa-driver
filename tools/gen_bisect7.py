#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect7.py — B20: B15(unishare+CmdSelect) 转存 ASCII 编码验证编码根因"""
import os

B15 = r"E:\Deepseek\lj2400woa\build\bisect5\B15_cmdinj.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect7"
os.makedirs(OUT, exist_ok=True)

t = open(B15, encoding="utf-16").read()
open(os.path.join(OUT, "B20_ascii.gpd"), "w", encoding="ascii", newline="\n").write(t)
print("OK B20 ascii", len(t))
