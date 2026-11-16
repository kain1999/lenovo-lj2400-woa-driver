#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v4en.py — V10: Orientation 段全英文; V11: 只删中文注释(显示名保中文)
分岔: v4 组件对中文的敏感点在显示名还是注释"""
import re, os

USH = r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak"
OUT = r"E:\Deepseek\lj2400woa\build\v4s"

def read_gpd(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    return b.decode('utf-8-sig', errors='replace')

ush = read_gpd(USH)

def feat_block(t, name):
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(name), t)
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
    return t[m.start():j + 1]

# 我们的 Orientation 段(从 S_Orientation 提取)
s = read_gpd(os.path.join(OUT, 'S_Orientation.gpd'))
blk = feat_block(s, 'Orientation')

# V10: 中文 -> 英文
en = blk.replace('"纵向"', '"Portrait"').replace('"横向"', '"Landscape"')
en = re.sub(r'(\*%[^\r\n]*)', lambda m: '*% english note', en)  # 注释全换
v10 = ush.replace(feat_block(ush, 'Orientation'), en)
open(os.path.join(OUT, 'V10_orien_en.gpd'), 'wb').write(v10.encode('utf-16'))

# V11: 删含非 ASCII 的注释行, 显示名保中文
def strip_cn_comments(t):
    lines = t.split('\n')
    out = []
    for ln in lines:
        if ln.strip().startswith('*%') and any(ord(c) > 127 for c in ln):
            continue
        out.append(ln)
    return '\n'.join(out)

cn_note_free = strip_cn_comments(blk)
v11 = ush.replace(feat_block(ush, 'Orientation'), cn_note_free)
open(os.path.join(OUT, 'V11_orien_ncn.gpd'), 'wb').write(v11.encode('utf-16'))

# V12: 显示名英文但注释原样(中文注释)
en_name = blk.replace('"纵向"', '"Portrait"').replace('"横向"', '"Landscape"')
v12 = ush.replace(feat_block(ush, 'Orientation'), en_name)
open(os.path.join(OUT, 'V12_orien_enname.gpd'), 'wb').write(v12.encode('utf-16'))
print('OK V10/V11/V12')
