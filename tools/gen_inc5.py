#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc5.py — A10a: DOC_SETUP.17->16; A10b: Duplex 段去全部 CmdSelect"""
import os

SRC = r"E:\Deepseek\lj2400woa\build\inc4\A9a_dupnocon.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc5"
os.makedirs(OUT, exist_ok=True)

t = open(SRC, encoding="ascii").read()

a10a = t.replace('*Order: DOC_SETUP.17', '*Order: DOC_SETUP.16')

import re
a10b = re.sub(r'\n\s*\*Command: CmdSelect\s*\{\s*\*Order: DOC_SETUP\.17\s*\*Cmd: "[^"]*"\s*\}', '', t)
open(os.path.join(OUT, "A10a_order16.gpd"), "w", encoding="ascii", newline="\r\n").write(a10a)
open(os.path.join(OUT, "A10b_nocmd.gpd"), "w", encoding="ascii", newline="\r\n").write(a10b)
print("OK A10a/A10b", len(a10a), len(a10b))
