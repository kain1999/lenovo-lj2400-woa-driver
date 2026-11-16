#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc.py — 从 unishare 成功基线逐段逼近全量 GPD (A2-A6, 全部 ASCII/GBK 编码)"""
import re, os

USH = r"C:\Windows\System32\spool\drivers\x64\3\unishare.gpd"
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc"
os.makedirs(OUT, exist_ok=True)

ush = open(USH, encoding="utf-8").read()
full = open(FULL, encoding="utf-16").read()

def extract(t, pat):
    m = re.search(pat, t)
    if not m:
        return ''
    return m.group(1)

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

job_cmds = '\n'.join(filter(None, [cmd_block(full, 'CmdStartJob'), cmd_block(full, 'CmdStartDoc'), cmd_block(full, 'CmdEndJob')]))
res_feat = feat_block(full, 'Resolution')
paper_feat = feat_block(full, 'PaperSize')
other_feats = '\n'.join(filter(None, [
    feat_block(full, 'MediaType'), feat_block(full, 'TonerSave'), feat_block(full, 'Sleep'),
    feat_block(full, 'Duplex'), feat_block(full, 'ColorMode'), feat_block(full, 'Halftone'),
    feat_block(full, 'InputBin'), feat_block(full, 'Orientation'),
]))
# 其他全局命令(CmdEndRaster/CmdSendBlockData/CmdCR/LF/FF/EjectPage 等)
other_cmds = '\n'.join(filter(None, [
    cmd_block(full, 'CmdEndRaster'), cmd_block(full, 'CmdSendBlockData'),
]))
global_attrs = '\n'.join(filter(None, [
    extract(full, r'(\*EjectPageWithFF\?: TRUE\n)'),
    extract(full, r'(\*CursorXAfterSendBlockData: \w+\n)'),
    extract(full, r'(\*CursorYAfterSendBlockData: \w+\n)'),
    extract(full, r'(\*OutputDataFormat: \w+\n)'),
]))

a2 = ush + '\n' + job_cmds + '\n'
a3 = a2 + '\n' + res_feat + '\n'
a4 = a3 + '\n' + paper_feat + '\n'
a5 = a4 + '\n' + other_feats + '\n' + other_cmds + '\n' + global_attrs + '\n'
a6 = a5.replace('*Include:        "StdNames.gpd"', '*Include:        "StdNames.gpd"\n*Include:        "MSXPSINC.GPD"')

for n, body in (('A2_jobcmds', a2), ('A3_res', a3), ('A4_paper', a4), ('A5_allfeat', a5), ('A6_xpsinc', a6)):
    open(os.path.join(OUT, n + '.gpd'), 'w', encoding='gbk', newline='\r\n').write(body)
    print('OK', n, len(body))
