#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_y4.py — Y4 = Y3 + Resolution 段替换(300/600/HQ1200 + 栅格命令链)
验证 <1B>*t600R<1B>&u600D<1B>*r0A<1B>*b0M / CmdSendBlockData <1B>*b<W>"""
import re, os

ORIG = r"E:\Deepseek\lj2400woa\build\GENIBM9.GPD.orig.bak"
FULL = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8"

orig = open(ORIG, encoding="utf-8").read()
if '\x00' in orig[:200]:
    orig = open(ORIG, encoding="utf-16").read()
full = open(FULL, encoding="utf-16").read()

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

def decon(t):
    return re.sub(r'\s*\*Constraints:.*\n', '\n', t)

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

trip = '\n'.join(filter(None, [cmd_block(full, 'CmdStartJob'), cmd_block(full, 'CmdStartDoc'), cmd_block(full, 'CmdEndJob')]))
trip = ''.join(c if ord(c) < 128 else '?' for c in trip)

paper = clean(feat_block(full, 'PaperSize'))
dup = clean(feat_block(full, 'Duplex')).replace('*Feature: Duplex', '*Feature: MyDuplex')
res = clean(feat_block(full, 'Resolution'))
# 语法修正: 动态参数 #R/#D 必须在引号外(嵌串内=字面量)
res = res.replace('"<1B>*t#R<1B>&u#D<1B>*r0A<1B>*b0M"', '"<1B>*t" #R "<1B>&u" #D "<1B>*r0A<1B>*b0M"')
res = res.replace('"<1B>*t#R"', '"<1B>*t" #R').replace('<1B>&u#D', '<1B>&u" #D')

m = re.search(r'(\*Feature:\s+PaperSize\s*\{)', orig)
i = m.end() - 1
depth = 0
j = i
while j < len(orig):
    if orig[j] == '{':
        depth += 1
    elif orig[j] == '}':
        depth -= 1
        if depth == 0:
            break
    j += 1
y4 = orig[:m.start()] + paper + orig[j + 1:]

# 替换原版 Resolution 段
m2 = re.search(r'(\*Feature:\s+Resolution\s*\{)', y4)
i2 = m2.end() - 1
depth = 0
j2 = i2
while j2 < len(y4):
    if y4[j2] == '{':
        depth += 1
    elif y4[j2] == '}':
        depth -= 1
        if depth == 0:
            break
    j2 += 1
y4 = y4[:m2.start()] + res + y4[j2 + 1:]

y4 += '\n' + clean(feat_block(full, 'MediaType')) + '\n\n'
y4 += dup + '\n\n'
y4 += clean(feat_block(full, 'TonerSave')) + '\n\n'
y4 += clean(feat_block(full, 'Sleep')) + '\n\n'
y4 += cmd_block(full, 'CmdEndRaster') + '\n'
y4 += trip + '\n'
y4 = decon(y4)

open(os.path.join(OUT, "Y4_res.gpd"), "w", encoding="ascii", newline="\r\n").write(y4)
print("OK Y4", len(y4))
