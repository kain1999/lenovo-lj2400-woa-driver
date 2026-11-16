#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_gbk.py — 全量静态 GPD 转 GBK(ANSI, 保留中文显示名)"""
SRC = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
DST = r"E:\Deepseek\lj2400woa\build\LJ2405D_ansi.gpd"

t = open(SRC, encoding="utf-16").read()
open(DST, "w", encoding="gbk", newline="\r\n").write(t)
print("OK GBK", len(t))
