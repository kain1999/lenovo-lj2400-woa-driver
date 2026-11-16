#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect5.py — B14: unishare+最简单A4纸型; B15: unishare LETTER 注入 CmdSelect"""
import re, os

USH = r"C:\Windows\System32\spool\drivers\x64\3\unishare.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect5"
os.makedirs(OUT, exist_ok=True)

ush = open(USH, encoding="utf-8").read()

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

b14 = replace_feature(ush, "PaperSize", """*Feature: PaperSize
{
    *DefaultOption: ISOA4
    *Name: "Paper Size"

    *Option: ISOA4
    {
        *Name: "A4"
        *Command: CmdSelect { *Order: DOC_SETUP.16 *Cmd: "<1B>&l4096a26a6d1E" }
        *PageDimensions: PAIR(9921, 14031)
        *PrintableArea: PAIR(9521, 13631)
        *PrintableOrigin: PAIR(200, 200)
    }
}
""")

b15 = ush.replace('''    *Option: LETTER
    {
        *Name: "Letter"
''', '''    *Option: LETTER
    {
        *Name: "Letter"
        *Command: CmdSelect { *Order: DOC_SETUP.16 *Cmd: "<1B>&l4096a2a6d1E" }
''')

open(os.path.join(OUT, "B14_minA4.gpd"), "wb").write(b14.encode("utf-16"))
open(os.path.join(OUT, "B15_cmdinj.gpd"), "wb").write(b15.encode("utf-16"))
print("OK B14/B15", len(b14), len(b15))
