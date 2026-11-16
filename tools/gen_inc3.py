#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc3.py — A3a 成功基线 + 逐 feature 注入定位
A8a MediaType / A8b InputBin / A8c Duplex / A8d TonerSave / A8e Sleep
A8f ColorMode+Halftone / A8g 全局属性 / A8h 全局命令(CmdEndRaster等)
全部显示名英文占位。
"""
import re, os

INC2 = r"E:\Deepseek\lj2400woa\build\inc2\A3a_enname.gpd"   # A3a = unishare + 全量Resolution(英文名)
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc3"
os.makedirs(OUT, exist_ok=True)

base = open(INC2, encoding="gbk").read()
full = open(FULL, encoding="utf-16").read()

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
    return t[m.start():j + 1]

def cmd_block(t, name):
    m = re.search(r'(\*Command:\s+%s\s*\{)' % re.escape(name), t)
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

def dezh(s):
    mapping = {
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
    for k, v in mapping.items():
        s = s.replace(k, v)
    return ''.join(c if ord(c) < 128 else '?' for c in s)

def clean(block):
    # 引号内中文映射 + 全文 ASCII 消毒
    def rm(m):
        return '"%s"' % dezh(m.group(1))
    s = re.sub(r'"([^"]*)"', rm, block)
    return ''.join(c if ord(c) < 128 else '?' for c in s)

cases = {}
cases['A8a_media'] = feat_block(full, 'MediaType')
cases['A8b_inputbin'] = feat_block(full, 'InputBin')
cases['A8c_duplex'] = feat_block(full, 'Duplex')
cases['A8d_toner'] = feat_block(full, 'TonerSave')
cases['A8e_sleep'] = feat_block(full, 'Sleep')
cases['A8f_colormode'] = feat_block(full, 'ColorMode') + '\n' + feat_block(full, 'Halftone')
cases['A8g_globalattrs'] = '\n'.join(filter(None, [
    re.search(r'\*EjectPageWithFF\?: TRUE', full) and '*EjectPageWithFF?: TRUE',
    re.search(r'\*CursorXAfterSendBlockData: (\w+)', full) and '*CursorXAfterSendBlockData: %s' % re.search(r'\*CursorXAfterSendBlockData: (\w+)', full).group(1),
    re.search(r'\*CursorYAfterSendBlockData: (\w+)', full) and '*CursorYAfterSendBlockData: %s' % re.search(r'\*CursorYAfterSendBlockData: (\w+)', full).group(1),
    re.search(r'\*OutputDataFormat: (\w+)', full) and '*OutputDataFormat: %s' % re.search(r'\*OutputDataFormat: (\w+)', full).group(1),
])) + '\n'
cases['A8h_globalcmds'] = cmd_block(full, 'CmdEndRaster') + '\n'

# Constraints 与 Constraints 行(全量)
cons = re.search(r'(\*Feature:\s*UIConstraints\s*\{)', full)
if cons:
    m = cons
    i = m.end() - 1
    depth = 0
    j = i
    while j < len(full):
        if full[j] == '{':
            depth += 1
        elif full[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    cases['A8i_uiconst'] = full[m.start():j + 1]

for n, blk in cases.items():
    blk = clean(blk) if not n.endswith('globalattrs') else blk
    body = base + '\n' + blk + '\n'
    open(os.path.join(OUT, n + '.gpd'), 'w', encoding='ascii', newline='\r\n').write(body)
    print('OK', n, len(body))
