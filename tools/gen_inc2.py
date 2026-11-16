#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc2.py — Resolution 段细分: A3a 英文名 / A3b 单选项无命令 / A3c 单选项+PJL命令"""
import re, os

INC = r"E:\Deepseek\lj2400woa\build\inc"
OUT = r"E:\Deepseek\lj2400woa\build\inc2"
os.makedirs(OUT, exist_ok=True)

a2 = open(os.path.join(INC, "A2_jobcmds.gpd"), encoding="gbk").read()
a3 = open(os.path.join(INC, "A3_res.gpd"), encoding="gbk").read()

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

res = feat_block(a3, "Resolution")

a3a = a2 + '\n' + res.replace('"分辨率"', '"Resolution"') + '\n'

b300 = res[res.find('    *Option: 300dpi'):]
b300 = b300[:b300.find('    }') + len('    }') + 1]
b600 = res[res.find('    *Option: 600dpi'):]
b600 = b600[:b600.find('    }') + len('    }') + 1]
head = res[:res.find('    *Option: 300dpi')]
a3b = a2 + '\n' + head + b600 + "\n}\n" + '\n'
a3c = a3b.replace('        *Name: "600dpi"',
                  '        *Name: "600dpi"\n        *Command: CmdSelect { *Order: DOC_SETUP.6 *Cmd: "@PJL SET RESOLUTION = 600<0A>" }')

for n, body in (('A3a_enname', a3a), ('A3b_single', a3b), ('A3c_pjlcmd', a3c)):
    open(os.path.join(OUT, n + '.gpd'), 'w', encoding='gbk', newline='\r\n').write(body)
    print('OK', n, len(body))
