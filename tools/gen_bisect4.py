#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect4.py — B12: 删三个数字开头 16K keyword 选项; B13: 16K keyword 改字母开头"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect4"
os.makedirs(OUT, exist_ok=True)

text = open(SRC, encoding="utf-16").read()

# B12: 删 16K_* 三个 Option 块 + 清除引用
def drop_option(t, kw):
    m = re.search(r'\*Option:\s+%s\s*\{' % re.escape(kw), t)
    if not m:
        return t
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
    return t[:m.start()] + t[j + 1:]

b12 = text
for kw in ('16K_195x270mm', '16K_184x260mm', '16K_197x273mm'):
    b12 = drop_option(b12, kw)
    b12 = re.sub(r',\s*%s(?=[,\s)])' % re.escape(kw), '', b12)
    b12 = re.sub(r'(?=[\s(,])%s,\s*' % re.escape(kw), '', b12)

# B13: keyword 改字母开头(Size16K_ 前缀), *Name 显示名不动
b13 = text.replace('16K_195x270mm', 'Size16K_195x270mm').replace('16K_184x260mm', 'Size16K_184x260mm').replace('16K_197x273mm', 'Size16K_197x273mm')

open(os.path.join(OUT, "B12_no16k.gpd"), "wb").write(b12.encode("utf-16"))
open(os.path.join(OUT, "B13_renamed.gpd"), "wb").write(b13.encode("utf-16"))
print("OK B12/B13", len(b12), len(b13))
