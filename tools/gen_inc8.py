#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc8.py — A13 细项 + A14 全量拼装(v3 ANSI 验证版)
A13b ColorMode(unishare式8bpp) / A13c Halftone / A13d PaperSize全量(英文名)
A14 = A3a + PaperSize全量 + MediaType + InputBin全量 + MyDuplex + TonerSave + Sleep
      + ColorMode(MONO) + Halftone + 全局属性 + CmdEndRaster
"""
import re, os

A3A = r"E:\Deepseek\lj2400woa\build\inc2\A3a_enname.gpd"
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8"
os.makedirs(OUT, exist_ok=True)

base = open(A3A, encoding="gbk").read()
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
    return t[m.start():j + 1:]

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
    return t[m.start():j + 1:]

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

# A13b ColorMode unishare 式 8bpp
a13b = base.replace('''*Feature: ColorMode
{
    *Name: "Color Mode"
    *DefaultOption: 24bpp
    *ConcealFromUI?: TRUE

    *Option: 24bpp
    {
        *Name: "24 bpp"
        *DevNumOfPlanes: 1
        *DevBPP: 24
        *DrvBPP: 24
    }
}''', '''*Feature: ColorMode
{
    *Name: "Color Mode"
    *DefaultOption: Mono8bpp
    *ConcealFromUI?: TRUE

    *Option: Mono8bpp
    {
        *Name: "8 bpp"
        *DevNumOfPlanes: 1
        *DevBPP: 8
        *DrvBPP: 8
    }
}''')
open(os.path.join(OUT, "A13b_col8bpp.gpd"), "w", encoding="ascii", newline="\r\n").write(a13b)

# A13c Halftone 单独
a13c = base + '\n' + clean(feat_block(full, 'Halftone')) + '\n'
open(os.path.join(OUT, "A13c_halftone.gpd"), "w", encoding="ascii", newline="\r\n").write(a13c)

# A13d PaperSize 全量(英文名)
a13d = base + '\n' + clean(feat_block(full, 'PaperSize')) + '\n'
open(os.path.join(OUT, "A13d_paper.gpd"), "w", encoding="ascii", newline="\r\n").write(a13d)

# A14 全量拼装
dup = feat_block(full, 'Duplex')
dup = clean(dup).replace('*Feature: Duplex', '*Feature: MyDuplex')
dup = dup.replace('*DefaultOption: OneSided', '*DefaultOption: OneSided')
# constraints 引用 PaperSize.* 保持(全量纸型到位)

a14 = base + '\n'
a14 += clean(feat_block(full, 'MediaType')) + '\n\n'
a14 += dup + '\n\n'
a14 += clean(feat_block(full, 'TonerSave')) + '\n\n'
a14 += clean(feat_block(full, 'Sleep')) + '\n\n'
a14 += '*EjectPageWithFF?: TRUE\n*CursorXAfterSendBlockData: AT_GRXDATA_START\n*CursorYAfterSendBlockData: NO_MOVE\n*OutputDataFormat: H_BYTE\n\n'
a14 += cmd_block(full, 'CmdEndRaster') + '\n'
open(os.path.join(OUT, "X2_nopaper.gpd"), "w", encoding="ascii", newline="\r\n").write(a14)
print("OK X2 len:", len(a14))
