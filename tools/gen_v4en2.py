#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_v4en2.py — V14: Orientation 段全英文化(含 feature 头显示名) + V15: 我们段原样但从 src 提取再清洗"""
import re, os

OUT = r"E:\Deepseek\lj2400woa\build\v4s"

def read_gpd(p):
    b = open(p, 'rb').read()
    return b.decode('utf-16') if b[:2] == b'\xff\xfe' else b.decode('utf-8-sig', errors='replace')

ush = read_gpd(r"E:\Deepseek\lj2400woa\build\unishare.gpd.x3.bak")
s = read_gpd(os.path.join(OUT, 'S_Orientation.gpd'))

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

blk = feat_block(s, 'Orientation')

# 全 ASCII 化: 引号内中文 -> 英文, 其余非 ASCII -> ?
def full_en(block):
    block = block.replace('方向', 'Orientation').replace('纵向', 'Portrait').replace('横向', 'Landscape')
    block = re.sub(r'\*%[^\r\n]*', lambda m: '*% note', block)
    return ''.join(c if ord(c) < 128 else '?' for c in block)

blk_v14 = full_en(blk)
# keyword 标准化
blk_v14 = blk_v14.replace('*Option: Portrait', '*Option: PORTRAIT').replace('*Option: Landscape', '*Option: LANDSCAPE_CC270').replace('*DefaultOption: Portrait', '*DefaultOption: PORTRAIT')

v14 = ush.replace(feat_block(ush, 'Orientation'), blk_v14)
open(os.path.join(OUT, 'V14_orien_fullen.gpd'), 'wb').write(v14.encode('utf-16'))

# 残留非 ASCII 检查
bad = [l for l in v14.split('\n') if any(ord(c) > 127 for c in l)]
print('OK V14', len(v14), '段外非ASCII行:', len(bad), bad[:3])
