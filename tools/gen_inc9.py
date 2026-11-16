#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc9.py — A14c replace 式拼装: unishare 的 PaperSize/InputBin/ColorMode 原位替换为我们的段
追加式改为替换式, 消除重复 feature 定义"""
import re, os

A3A = r"E:\Deepseek\lj2400woa\build\inc2\A3a_enname.gpd"
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc9"
os.makedirs(OUT, exist_ok=True)

base = open(A3A, encoding="gbk").read()
full = open(FULL, encoding="utf-16").read()

MAP = {
    '纸张来源': 'InputBin', '手动': 'Manual', '纸盒1': 'Tray1', '介质类型': 'MediaType',
    '普通纸': 'Plain', '薄纸': 'Thin', '厚纸': 'Thick', '特厚纸': 'UThick', '铜版纸': 'Cotton',
    '信封': 'Env', '厚信封': 'EnvThick', '薄信封': 'EnvThin', '再生纸': 'Recycled',
    '分辨率': 'Resolution', '纸张大小': 'PaperSize', '4 x 6 英寸': '4x6in',
    '明信片': 'Postcard', '明信片 2 (双面)': 'Postcard2', 'Y4 信封': 'Y4Env',
    '[CUSTOM1]用户自定义尺寸': '[CUSTOM1]Custom', '[CUSTOM2]用户自定义尺寸': '[CUSTOM2]Custom',
    '[CUSTOM3]用户自定义尺寸': '[CUSTOM3]Custom', '双面打印设置': 'Duplex',
    '无': 'None', '长边': 'LongEdge', '短边': 'ShortEdge', '省墨模式': 'TonerSave',
    '关': 'OFF', '开': 'ON', '休眠时间[分]': 'Sleep', '打印机默认值': 'PrinterDefault',
    '黑白': 'Mono',
}
def clean(block):
    def rm(m):
        s = m.group(1)
        for k, v in MAP.items():
            s = s.replace(k, v)
        return '"%s"' % s
    s = re.sub(r'"([^"]*)"', rm, block)
    return ''.join(c if ord(c) < 128 else '?' for c in s)

def block_of(t, kind, name):
    m = re.search(r'(\*%s:\s+%s\s*\{)' % (kind, re.escape(name)), t)
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
    return t[m.start():j + 1]

def replace_block(t, kind, name, new):
    old = block_of(t, kind, name)
    if not old:
        return t + '\n' + new + '\n'
    return t.replace(old, new)

dup = clean(block_of(full, 'Feature', 'Duplex')).replace('*Feature: Duplex', '*Feature: MyDuplex')

t = base
t = replace_block(t, 'Feature', 'PaperSize', clean(block_of(full, 'Feature', 'PaperSize')))
t = replace_block(t, 'Feature', 'InputBin', clean(block_of(full, 'Feature', 'InputBin')))
t = replace_block(t, 'Feature', 'ColorMode', clean(block_of(full, 'Feature', 'ColorMode')))
t += '\n' + clean(block_of(full, 'Feature', 'MediaType')) + '\n\n'
t += dup + '\n\n'
t += clean(block_of(full, 'Feature', 'TonerSave')) + '\n\n'
t += clean(block_of(full, 'Feature', 'Sleep')) + '\n\n'
t += '*EjectPageWithFF?: TRUE\n*CursorXAfterSendBlockData: AT_GRXDATA_START\n*CursorYAfterSendBlockData: NO_MOVE\n*OutputDataFormat: H_BYTE\n\n'
t += block_of(full, 'Command', 'CmdEndRaster') + '\n'

open(os.path.join(OUT, "A14c_replace.gpd"), "w", encoding="ascii", newline="\r\n").write(t)
print("OK A14c", len(t))
