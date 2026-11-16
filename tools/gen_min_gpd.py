#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_min_gpd.py — 生成 5 版渐进 v3 GPD (M1-M5) 用于 AddPrinter 二分定位 0x3EB 根因
M1: 极简骨架(2 纸型+3 分辨率+栅格命令, 全英文, 无 Include MSXPSINC, 无 *Order on 全局命令)
M2: M1 + 全部 26 纸型(含 CUSTOMSIZE/CustomMediaSize, CmdSelect 静态)
M3: M2 + 中文选项 Name
M4: M3 + 全 feature(MediaType/InputBin/Duplex/TonerSave/Sleep 纯数字 keyword + 约束)
M5: M4 + *Include MSXPSINC.GPD
"""
import os

BASE = r"E:\Deepseek\lj2400woa\build"
OUT = os.path.join(BASE, "min")

def paper(kw, disp, w, h, code, zh=False):
    name = disp if zh else kw
    dim = (int(w * 1200 / 25.4 + 0.5), int(h * 1200 / 25.4 + 0.5))
    o = ['    *Option: %s' % kw,
         '    {',
         '        *Name: "%s"' % name,
         '        *Command: CmdSelect',
         '        {',
         '            *Order: DOC_SETUP.16',
         '            *Cmd: "<1B>&l4096a%da6d1E"' % code,
         '        }',
         '        *PageDimensions: PAIR(%d, %d)' % dim,
         '        *PrintableArea: PAIR(%d, %d)' % (dim[0] - 400, dim[1] - 400),
         '        *PrintableOrigin: PAIR(200, 200)',
         '    }']
    return "\n".join(o)

def custom(kw, zh=False):
    name = '用户自定义%d' % {"CUSTOM1": 1, "CUSTOM2": 2, "CUSTOM3": 3}.get(kw, 0) if zh else kw
    o = ['    *Option: %s' % kw,
         '    {',
         '        *Name: "%s"' % name,
         '        *MinSize: PAIR(3600, 6000)',
         '        *MaxSize: PAIR(10200, 16800)',
         '        *MaxPrintableWidth: 9800',
         '        *MinLeftMargin: 200',
         '        *CenterPrintable?: FALSE',
         '        *Command: CmdSelect',
         '        {',
         '            *Order: DOC_SETUP.16',
         '            *Cmd: "<1B>&u1200D<1B>*c4960X<1B>*c7016Y<1B>*c0P"',
         '        }',
         '    }']
    return "\n".join(o)

PAPERS = [
    ("ISOA4", "A4", 210.0, 297.0, 26),
    ("NorthAmericaLetter", "Letter", 215.9, 279.4, 2),
    ("NorthAmericaLegal", "Legal", 215.9, 355.6, 3),
    ("ISOA5", "A5", 148.0, 210.0, 25),
    ("ISODLEnvelope", "DL", 110.0, 220.0, 90),
]

def res_block():
    return """*Feature: Resolution
{
    *Name: "Resolution"
    *DefaultOption: 600dpi
    *Option: 300dpi
    {
        *Name: "300dpi"
        *DPI: PAIR(300, 300)
        *TextDPI: PAIR(300, 300)
        *SpotDiameter: 100
        *Command: CmdSelect { *Order: DOC_SETUP.6 *Cmd: "@PJL SET RESOLUTION = 300<0A>" }
        *Command: CmdBeginRaster { *Cmd : "<1B>*t300R<1B>&u300D<1B>*r0A<1B>*b0M" }
    }
    *Option: 600dpi
    {
        *Name: "600dpi"
        *DPI: PAIR(600, 600)
        *TextDPI: PAIR(600, 600)
        *SpotDiameter: 100
        *Command: CmdSelect { *Order: DOC_SETUP.6 *Cmd: "@PJL SET RESOLUTION = 600<0A>" }
        *Command: CmdBeginRaster { *Cmd : "<1B>*t600R<1B>&u600D<1B>*r0A<1B>*b0M" }
    }
    *Option: HQ1200
    {
        *Name: "1200dpi"
        *DPI: PAIR(1200, 1200)
        *TextDPI: PAIR(1200, 1200)
        *SpotDiameter: 100
        *Command: CmdSelect { *Order: DOC_SETUP.6 *Cmd: "@PJL SET RESOLUTION = 1200<0A>@PJL SET RAS1200MODE = TRUE<0A>" }
        *Command: CmdBeginRaster { *Cmd : "<1B>*t1200R<1B>&u1200D<1B>*r0A<1B>*b0M" }
    }
}
"""

def common_commands(with_job_order=True):
    order1 = '    *Order: JOB_SETUP.1\n' if with_job_order else ''
    order2 = '    *Order: DOC_SETUP.14\n' if with_job_order else ''
    return """*Command: CmdStartJob
{
%s    *Cmd : "<1B>%%-12345X@PJL<0A>@PJL JOB NAME=<22>Lenovo print job<22><0A>"
}
*Command: CmdStartDoc
{
%s    *Cmd : "@PJL ENTER LANGUAGE = PCL<0A>"
}
*Command: CmdEndJob
{
    *Cmd : "@PJL EOJ NAME=<22>Lenovo print job<22><0A><1B>%%-12345X"
}
*Command: CmdCR { *Cmd : "<0D>" }
*Command: CmdLF { *Cmd : "<0A>" }
*Command: CmdFF { *Cmd : "<0C>" }
*Command: CmdEndRaster { *Cmd : "<1B>*rB" }
*Command: CmdSendBlockData { *Cmd : "<1B>*b" %%d{NumOfDataBytes}"W" }
*EjectPageWithFF?: TRUE
*CursorXAfterSendBlockData: AT_GRXDATA_START
*CursorYAfterSendBlockData: NO_MOVE
*OutputDataFormat: H_BYTE
""" % (order1, order2)

def header(gpd, include_msxps=False):
    inc = '*Include:        "MSXPSINC.GPD"\n' if include_msxps else ''
    return """*GPDSpecVersion: "1.0"
*GPDFileVersion: "1.0"
*GPDFileName:    "%s"
*Include:        "StdNames.gpd"
%s*ModelName:      "Lenovo LJ2405D"
*MasterUnits:    PAIR(1200, 1200)
*PrinterType:    PAGE
*MaxCopies:      1
""" % (gpd, inc)

os.makedirs(OUT, exist_ok=True)

# M1
m1 = header("MINT.GPD") + """*Feature: PaperSize
{
    *Name: "PaperSize"
    *DefaultOption: ISOA4
""" + "\n".join(paper(k, d, w, h, c) for k, d, w, h, c in PAPERS[:2]) + "\n}\n\n" + res_block() + "\n" + common_commands(False)
write = lambda n, s: open(os.path.join(OUT, n), "wb").write(s.encode("utf-16"))
write("MINT.gpd", m1)

# M2
m2 = header("M2.GPD") + """*Feature: PaperSize
{
    *Name: "PaperSize"
    *DefaultOption: ISOA4
""" + "\n".join(paper(k, d, w, h, c) for k, d, w, h, c in PAPERS) + "\n" + "\n".join(
    custom(k) for k in ("CUSTOM1", "CUSTOM2", "CUSTOM3", "CustomMediaSize")) + "\n}\n\n" + res_block() + "\n" + common_commands(False)
write("M2.gpd", m2)

# M3
m3 = header("M3.GPD") + """*Feature: PaperSize
{
    *Name: "纸张大小"
    *DefaultOption: ISOA4
""" + "\n".join(paper(k, d, w, h, c, zh=True) for k, d, w, h, c in PAPERS) + "\n" + "\n".join(
    custom(k, zh=True) for k in ("CUSTOM1", "CUSTOM2", "CUSTOM3", "CustomMediaSize")) + "\n}\n\n" + res_block().replace('*Name: "Resolution"', '*Name: "分辨率"').replace('*Name: "300dpi"', '*Name: "300dpi"') + "\n" + common_commands(False)
write("M3.gpd", m3)

# M4 = M3 + 全 feature(与 gen_gpd.py 同构: MediaType/InputBin/Duplex/TonerSave/Sleep 数字 keyword + 约束)
m4 = header("M4.GPD") + open(os.path.join(BASE, "v3", "LJ2405D.gpd"), encoding="utf-16").read()
# M4 直接用 v3 全量 GPD(即最终形态)
write("M4.gpd", m4)

# M5 = M4 + Include MSXPSINC
m4t = open(os.path.join(BASE, "v3", "LJ2405D.gpd"), encoding="utf-16").read()
m5 = m4t.replace('*Include:        "StdNames.gpd"', '*Include:        "StdNames.gpd"\n*Include:        "MSXPSINC.GPD"')
write("M5.gpd", m5)
print("OK: MINT/M2/M3/M4/M5 ->", OUT)
