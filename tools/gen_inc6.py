#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc6.py — A11a: Duplex 标准keyword版; A11b: ColorMode/Halftone 删重注入版"""
import os, re

INC5 = r"E:\Deepseek\lj2400woa\build\inc5\A10a_order16.gpd"   # A3a + Duplex(order16)
INC3 = r"E:\Deepseek\lj2400woa\build\inc3"
OUT = r"E:\Deepseek\lj2400woa\build\inc6"
os.makedirs(OUT, exist_ok=True)

t = open(INC5, encoding="ascii").read()
a11a = t.replace('*DefaultOption: OneSided', '*DefaultOption: SIMPLEX') \
        .replace('*Option: OneSided', '*Option: SIMPLEX') \
        .replace('*Option: DuplexNoTumble', '*Option: VERTICAL') \
        .replace('*Option: DuplexTumble', '*Option: HORIZONTAL')
open(os.path.join(OUT, "A11a_stdkey.gpd"), "w", encoding="ascii", newline="\r\n").write(a11a)

# A11b: base(A8a) 删 unishare ColorMode, 注入全量 ColorMode(英文名)+Halftone(英文名)
base = open(os.path.join(INC3, "A8a_media.gpd"), encoding="gbk").read()
full = open(r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd", encoding="utf-16").read()

def feat_block(t, name):
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(name), t)
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

def drop_feature(t, name):
    b = feat_block(t, name)
    return t.replace(b, '') if b else t

base_nocol = drop_feature(base, 'ColorMode')

def dezh(s):
    mapping = {
        '黑白': 'Mono', '双面打印设置': 'Duplex', '无': 'None', '长边': 'LongEdge',
        '短边': 'ShortEdge', '省墨模式': 'TonerSave', '关': 'OFF', '开': 'ON',
        '休眠时间[分]': 'Sleep', '打印机默认值': 'PrinterDefault', '介质类型': 'MediaType',
    }
    for k, v in mapping.items():
        s = s.replace(k, v)
    return s

col = feat_block(full, 'ColorMode')
hal = feat_block(full, 'Halftone')
col = re.sub(r'"([^"]*)"', lambda m: '"%s"' % dezh(m.group(1)), col)
hal = re.sub(r'"([^"]*)"', lambda m: '"%s"' % dezh(m.group(1)), hal)
col = ''.join(c if ord(c) < 128 else '?' for c in col)
hal = ''.join(c if ord(c) < 128 else '?' for c in hal)

a11b = base_nocol + '\n' + col + '\n\n' + hal + '\n'
open(os.path.join(OUT, "A11b_color.gpd"), "w", encoding="ascii", newline="\r\n").write(a11b)
print("OK A11a/A11b", len(a11a), len(a11b))
