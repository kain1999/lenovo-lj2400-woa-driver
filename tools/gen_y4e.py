#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_y4e.py — Y4e = Y3 + 仅改 DPI 240x216 -> 600x600 (单变量)"""
import os

SRC = r"E:\Deepseek\lj2400woa\build\inc8\Y3_feats.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8\Y4e_dpi.gpd"

t = open(SRC, encoding="ascii").read()
t2 = t.replace('*DPI: PAIR(240, 216)', '*DPI: PAIR(600, 600)').replace('*TextDPI: PAIR(240, 216)', '*TextDPI: PAIR(600, 600)')
open(OUT, "w", encoding="ascii", newline="\r\n").write(t2)
print("OK Y4e", len(t2))
