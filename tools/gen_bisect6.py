#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect6.py — B16: CmdSelect 多行块形态; B17: 单行但 Order=DOC_SETUP.8"""
import os

USH = r"C:\Windows\System32\spool\drivers\x64\3\unishare.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect6"
os.makedirs(OUT, exist_ok=True)

ush = open(USH, encoding="utf-8").read()

b16 = ush.replace('''    *Option: LETTER
    {
        *Name: "Letter"
''', '''    *Option: LETTER
    {
        *Name: "Letter"
        *Command: CmdSelect
        {
            *Order: DOC_SETUP.16
            *Cmd: "<1B>&l4096a2a6d1E"
        }
''')

b17 = ush.replace('''    *Option: LETTER
    {
        *Name: "Letter"
''', '''    *Option: LETTER
    {
        *Name: "Letter"
        *Command: CmdSelect { *Order: DOC_SETUP.8 *Cmd: "<1B>&l4096a2a6d1E" }
''')

open(os.path.join(OUT, "B16_multiline.gpd"), "wb").write(b16.encode("utf-16"))
open(os.path.join(OUT, "B17_order8.gpd"), "wb").write(b17.encode("utf-16"))
print("OK B16/B17", len(b16), len(b17))
