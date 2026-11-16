#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_gpd.py — Lenovo LJ24/LJ26/M74/M76 全系列(27 型号) Windows v4 打印驱动包(WoA/ARM64 兼容)生成器
================================================================================================
数据源(严格):
  1) E:\Deepseek\lj2400lin\analysis\ppd_extract.json
     —— 选项与约束的唯一事实来源(Duplex/MediaType/InputSlot/TonerSave/Sleep/UIConstraints/默认值)。
  2) 原始 CUPS PPD(*-cups-en.ppd)
     —— PageSize 选项列表(25 项=22 实纸型+CUSTOM1/2/3)、DefaultPageSize、HWMargins。
        JSON 的 PageSize_opts 只有 20 项(漏 B5/B6/4x6/DoublePostcardRotated/EnvYou4)，
        属数据缺陷，以原始 PPD 为准(与 27 个 PPD 实测一致)。
  3) E:\Deepseek\lj2400lin\analysis\rawtobr3_strings.txt
     —— 所有命令字符串的唯一来源(行号+偏移写进 GPD 注释)，禁止自创命令。

产出(E:\Deepseek\lj2400woa\driver\):
  - LJ2400WOA.INF                        (UTF-16 LE BOM; v4 INF, ClassVer=4.0, DriverIsolation=2)
  - <MODEL>.gpd               ×27        (UTF-16 LE BOM; Unidrv 数据包 GPD, MXDW/unishare 骨架)
  - <MODEL>-manifest.ini      ×27        (v4 manifest; RequiredFiles 全部为系统内置件)
  - <MODEL>-pipelineconfig.xml×27        (v4 管道配置名必须与 DataFile 基名一致 — prnms005/unishare 实证;
                                          单一共享名 spooler 不会解析, 故按 DataFile 基名逐型号生成)

设计要点(与参照样本逐条对齐):
  - GPD 骨架: unishare.gpd/MXDW.gpd (spool\drivers\x64\3) —— *GPDSpecVersion/*GPDFileName/
    *ModelName/*MasterUnits PAIR(1200,1200)/*PrinterType PAGE/*MaxCopies 1/*Include StdNames+MSXPSINC。
  - raster 命令: unishare 的 CmdBeginRaster/CmdEndRaster/CmdSendBlockData(%d{NumOfDataBytes})
    + rawtobr3 的 <1B>*r0A / <1B>*rB; 压缩显式 NONE=<1B>*b0M(不发 1030M)。
  - HQ1200 几何推断: capability_matrix §8.5 "实际栅格 1200dpi + RAS1200MODE=TRUE + PAPERFEEDSPEED"
    → *DPI: PAIR(1200,1200), PCL *t1200R+&u1200D(中等置信, 报告标注待真机验证)。
  - PJL 顺序: CmdSelect 带 *Order: DOC_SETUP.N(GENIBM9.GPD 生产实证语法), PJL SET(2..6) →
    CmdStartDoc(14)=ENTER LANGUAGE=PCL → PCL 命令(16..17); 运行期用安装+测试页抓流验证。
  - 纸型命令: rawtobr3 129-146 行的 <1B>&l4096a<CODE>a6d1E 原样复制; 无码纸型走 PCL5 标准
    自定义尺寸路由 <1B>&u600D<1B>*c#X<1B>*c#Y<1B>*c0P(点数=600dpi, 维度精确)。
  - USB 硬件 ID: LEXHL13A.INF 实测双写形式(USBPRINT\\xxx 与裸 xxx), 4 个已知 ID 挂对应型号。
"""
import json
import os
import re
import glob as _glob
import uuid
import random
import sys

BASE   = r"E:\Deepseek\lj2400woa"
DRIVER = os.path.join(BASE, "driver")
BUILD  = os.path.join(BASE, "build")
PPDJSON  = r"E:\Deepseek\lj2400lin\analysis\ppd_extract.json"
PPD_GLOB = r"E:\Deepseek\lj2400lin\deb_extract\uos_print\data.tar.xz.d\._usr_share_cups_model_lenovo_lenovo-*-cups-en.ppd"
STRINGS  = r"E:\Deepseek\lj2400lin\analysis\rawtobr3_strings.txt"

INF_NAME = "LJ2400WOA.INF"
PROVIDER = "Lenovo (WoA port)"
DISK1    = "Lenovo LJ24/LJ26/M74/M76 WoA Driver Disk"

# rawtobr3_strings.txt 中确认的 USB 硬件 ID(LEXHL13A.INF 实测格式, 双写: 带前缀+裸 ID)
# 注意: LEXHL13A.INF 里还有 LJ2455D=LENOVOLJ2455D6220, 但本 27 型号 PPD 族不含 LJ2455D
# (Brother 原始驱动多覆盖一个型号), 该 ID 无对应型号可挂, 不写入 INF, 在报告中说明。
USB_IDS = {
    "LJ2405D":  r"USBPRINT\LENOVOLJ2405D6330",
    "LJ2605D":  r"USBPRINT\LENOVOLJ2605DDB31",
    "LJ2655DN": r"USBPRINT\LENOVOLJ2655DN2C9A",
}
USB_UNMAPPED = {"LJ2455D": r"USBPRINT\LENOVOLJ2455D6220"}  # 无对应型号, 仅记录

# 纸型表: ppd_kw, gpd_kw, w_mm, h_mm, PCL 码(None→*c 自定义路由), 证据/置信注释
PAPERS = [
    ("Letter",    "NorthAmericaLetter",           215.9,   279.4, 2,    "rawtobr3 strings=144 行"),
    ("Legal",     "NorthAmericaLegal",            215.9,   355.6, 3,    "rawtobr3 strings=146 行"),
    ("Executive", "NorthAmericaExecutive",        184.15,  266.7, 1,    "rawtobr3 strings=142 行"),
    ("FanFoldGermanLegal", "OtherMetricFolio",    215.9,   330.2, 100,  "rawtobr3 strings=140 行(任务书猜 101, 以 strings 为准)"),
    ("A4",        "ISOA4",                        210.0,   297.0, 26,   "rawtobr3 strings=143 行"),
    ("A5",        "ISOA5",                        148.0,   210.0, 25,   "rawtobr3 strings=138 行(任务书猜 37, 以 strings 为准)"),
    ("A6",        "ISOA6",                        105.0,   148.0, 24,   "rawtobr3 strings=133 行; 码 24=A6 为 LOW 置信(HP 标准=99)"),
    ("Env10",     "NorthAmericaNumber10Envelope", 104.775, 241.3, 81,   "rawtobr3 strings=132 行"),
    ("EnvMonarch","NorthAmericaMonarchEnvelope",  98.425,  190.5, 80,   "rawtobr3 strings=130 行"),
    ("EnvDL",     "ISODLEnvelope",                110.0,   220.0, 90,   "rawtobr3 strings=135 行"),
    ("EnvC5",     "ISOC5Envelope",                162.0,   229.0, 91,   "rawtobr3 strings=139 行"),
    ("ISOB5",     "ISOB5Envelope",                176.0,   250.0, 44,   "rawtobr3 strings=137 行; HP PCL5 44=B5(ISO) 176x250, 中高置信"),
    ("B5",        "JISB5",                        182.0,   257.0, 45,   "rawtobr3 strings=141 行"),
    ("ISOB6",     "ISOB6",                        125.0,   176.0, None, "rawtobr3 无码 → *c 自定义尺寸路由(维度精确)"),
    ("B6",        "JISB6",                        128.0,   182.0, None, "任务书猜 46 无 strings 佐证, 禁自创 → *c 路由"),
    ("4x6",       "NorthAmerica4X6",              101.6,   152.4, 71,   "rawtobr3 strings=131 行; 71=4x6 为 LOW 置信(或=3x5)"),
    ("Postcard",  "JapanHagakiPostcard",          100.0,   148.0, 1024, "rawtobr3 strings=136 行; Brother 日系码段 LOW 置信"),
    ("DoublePostcardRotated", "JapanDoubleHagakiPostcard", 148.0, 200.0, 1038, "rawtobr3 strings=145 行(DHAGAKI=双面明信片); LOW 置信"),
    ("EnvYou4",   "JapanYou4Envelope",            105.0,   235.0, 1039, "rawtobr3 strings=129 行; LOW 置信"),
    ("195x270mm", "16K_195x270mm",                195.0,   270.0, None, "16K 无码 → *c 路由"),
    ("184x260mm", "16K_184x260mm",                184.0,   260.0, None, "16K 无码 → *c 路由"),
    ("197x273mm", "16K_197x273mm",                197.0,   273.0, None, "16K 无码 → *c 路由"),
]
# PPD 约束侧 kw → GPD PaperSize kw(仅与上表不同的项 + CUPS 内置 Custom)
CONSTRAINT_NAME_MAP = {
    "Custom": "CustomMediaSize",          # CUPS 内置自定义尺寸
    "Letter": "NorthAmericaLetter",
    "Legal":  "NorthAmericaLegal",
    "Executive": "NorthAmericaExecutive",
    "FanFoldGermanLegal": "OtherMetricFolio",
    "A4": "ISOA4", "A5": "ISOA5", "A6": "ISOA6",
    "Env10": "NorthAmericaNumber10Envelope",
    "EnvMonarch": "NorthAmericaMonarchEnvelope",
    "EnvDL": "ISODLEnvelope", "EnvC5": "ISOC5Envelope",
    "ISOB5": "ISOB5Envelope", "B5": "JISB5", "ISOB6": "ISOB6", "B6": "JISB6",
    "4x6": "NorthAmerica4X6",
    "Postcard": "JapanHagakiPostcard",
    "DoublePostcardRotated": "JapanDoubleHagakiPostcard",
    "EnvYou4": "JapanYou4Envelope",
    "195x270mm": "16K_195x270mm",
    "184x260mm": "16K_184x260mm",
    "197x273mm": "16K_197x273mm",
    "CUSTOM1": "CUSTOM1", "CUSTOM2": "CUSTOM2", "CUSTOM3": "CUSTOM3",
}
# PPD 约束侧 feature kw → GPD feature 名
CONSTRAINT_FEATURE_MAP = {
    "PageSize": "PaperSize",
    "InputSlot": "InputBin",
    "BrMediaType": "MediaType",
    "Duplex": "Duplex",
}

CUSTOM_MIN_MM = (76.2, 127.0)
CUSTOM_MAX_MM = (215.9, 355.6)
MASTER = 1200            # master units per inch (水平/垂直同值; 分辨率 300/600/1200 均可整除)
PCL_CUSTOM_DPI = 600     # *c 自定义路由用 600dpi 点数(&u600D 显式置标)

# MediaType: PPD kw → rawtobr3_strings.txt 65-73 行 @PJL SET MEDIATYPE = <值> (逐字节一致)
MEDIA = [
    ("PLAIN",        "普通纸",   "REGULAR"),
    ("THIN",         "薄纸",     "THIN"),
    ("THICK",        "厚纸",     "THICK"),
    ("THICKERPAPER2","特厚纸",   "THICK2"),
    ("BOND",         "铜版纸",   "BOND"),
    ("ENV",          "信封",     "ENVELOPES"),
    ("ENVTHICK",     "厚信封",   "ENVTHICK"),
    ("ENVTHIN",      "薄信封",   "ENVTHIN"),
    ("RECYCLED",     "再生纸",   "RECYCLED"),
]
INPUTBIN = [  # rawtobr3: SOURCETRAY = TRAY1(44 行)/MPTRAY(50 行); PCL &l#H 因跨 PJL/PCL 边界不发
    ("MANUAL", "手动",   "MPTRAY", "rawtobr3=50 行; &l2H(102 行, 手动进纸 PCL 标准)省略, 见报告"),
    ("TRAY1",  "纸盒1",  "TRAY1",  "rawtobr3=44 行"),
]
RESOLUTIONS = [  # PJL 部分抄 rawtobr3 38/39/40 行; PCL 部分 *t#R(94-97 行)+&u#D(110-113 行)
    ("300dpi",  "300dpi",               300, 300, 300,
     "@PJL SET RESOLUTION = 300\n@PJL SET RAS1200MODE = OFF\n",
     "<1B>*t300R<1B>&u300D",
     "rawtobr3=38 行(RESOLUTION = 300)+36 行(RAS1200MODE = OFF 清 1200 模式); PCL=94 行 *t300R+110 行 &u300D"),
    ("600dpi",  "600dpi",               600, 600, 600,
     "@PJL SET RESOLUTION = 600\n@PJL SET RAS1200MODE = OFF\n",
     "<1B>*t600R<1B>&u600D",
     "rawtobr3=39 行+36 行; PCL=95 行 *t600R+112 行 &u600D"),
    ("HQ1200",  "2400x600dpi (HQ1200)", 1200, 1200, 1200,
     "@PJL SET RESOLUTION = 1200\n@PJL SET PAPERFEEDSPEED=HALF\n@PJL SET RAS1200MODE = TRUE\n",
     "<1B>*t1200R<1B>&u1200D",
     "rawtobr3=40 行(RESOLUTION = 1200\\nPAPERFEEDSPEED=HALF 复合串)+34 行(RAS1200MODE = TRUE); "
     "几何推断见 capability_matrix §8.5(实际栅格 1200dpi, MEDIUM 置信); PCL=97 行 *t1200R+113 行 &u1200D"),
]
DUPLEX = [  # rawtobr3 98/99/100 行: &l0S/&l1S/&l2S; v4 PrintSchema 选项名
    ("OneSided",      "无",   0, "rawtobr3 strings=98 行 ESC&l0S"),
    ("DuplexNoTumble","长边", 1, "rawtobr3 strings=99 行 ESC&l1S(长边)"),
    ("DuplexTumble",  "短边", 2, "rawtobr3 strings=100 行 ESC&l2S(短边)"),
]
TONER = [  # rawtobr3 42/43 行, 自检逐字节比对
    ("OFF", "关", "@PJL SET ECONOMODE = OFF\n", "rawtobr3 strings=43 行"),
    ("ON",  "开", "@PJL SET ECONOMODE = ON\n",  "rawtobr3 strings=42 行"),
]
SLEEP = [  # rawtobr3 83 行 "@PJL SET AUTOSLEEP=" 前缀 + 动态值(81 行 DEFAULT 变体不用); PRINTER=设备默认不发
    ("PRINTER", "打印机默认值", None),
    ("2",  "2",  2),
    ("10", "10", 10),
    ("30", "30", 30),
]

CMD_START_JOB = '<1B>%%-12345X@PJL<0A>@PJL JOB NAME=<22>Lenovo print job<22><0A>'
CMD_START_DOC = '@PJL ENTER LANGUAGE = PCL<0A>'
CMD_END_JOB   = '@PJL EOJ NAME=<22>Lenovo print job<22><0A><1B>%%-12345X'

# CmdSelect 的 *Order 编排: PJL SET(2..6) → CmdStartDoc(14)=ENTER LANGUAGE=PCL → PCL(16..17)
ORDER = {
    "MediaType":  2,   # @PJL SET MEDIATYPE = ...   (rawtobr3 65-73 行)
    "TonerSave":  3,   # @PJL SET ECONOMODE = ...   (rawtobr3 42/43 行)
    "Sleep":      4,   # @PJL SET AUTOSLEEP=...     (rawtobr3 83 行前缀)
    "InputBin":   5,   # @PJL SET SOURCETRAY = ...  (rawtobr3 44-50 行)
    "Resolution": 6,   # @PJL SET RESOLUTION/RAS1200MODE/PAPERFEEDSPEED (37-41 行)
    "PaperSize":  16,  # PCL &l4096a<C>a6d1E        (129-146 行; ENTER LANGUAGE 之后)
    "Duplex":     17,  # PCL &l0S/1S/2S             (98-100 行)
}
DOC_ORDER = 14       # CmdStartDoc 的 DOC_SETUP 序号(须落在 6 与 16 之间)

GPD_HEADER_TPL = """*%
*% Lenovo @@MODEL@@ - Windows v4 Unidrv 数据驱动 GPD (WoA/ARM64 兼容, 纯数据包)
*% 生成器: gen_gpd.py; 骨架: unishare.gpd/MXDW.gpd (C:\\Windows\\System32\\spool\\drivers\\x64\\3)
*% 选项与约束唯一来源: ppd_extract.json(PageSize 取原始 CUPS PPD);
*% 命令字符串唯一来源: rawtobr3_strings.txt(行号随注释标注)。
*%
*GPDSpecVersion: "1.0"
*GPDFileVersion: "1.0"
*GPDFileName:    "@@GPD@@"
*Include:        "StdNames.gpd"
*Include:        "MSXPSINC.GPD"
*ModelName:      "Lenovo @@MODEL@@"
*MasterUnits:    PAIR(1200, 1200)
*PrinterType:    PAGE
*MaxCopies:      1
*PrintSchemaPrivateNamespaceURI: "http://www.lenovo.com/printing/woa/2024/LJ24"
"""

def mm2units(mm):
    """毫米 → master units (1200/inch), 四舍五入."""
    return int(mm * MASTER / 25.4 + 0.5)

def mm2pcl(mm, dpi=PCL_CUSTOM_DPI):
    """毫米 → PCL 点数(*c 自定义路由), 四舍五入."""
    return int(mm * dpi / 25.4 + 0.5)

def gpd_cmd_escape(s):
    """把 python 字符串(含 \\n)转成 GPD 命令串: \\n→<0A>, \\r→<0D>, ESC→<1B>, "→<22>, %→%%."""
    out = []
    for ch in s:
        if ch == "\n":   out.append("<0A>")
        elif ch == "\r": out.append("<0D>")
        elif ch == "\x1b": out.append("<1B>")
        elif ch == '"':  out.append("<22>")
        elif ch == "%":  out.append("%%")
        else:            out.append(ch)
    return "".join(out)

def build_paper_option(ppd_kw, gpd_kw, w_mm, h_mm, code, conf, display):
    o = []
    o.append('    *Option: %s' % gpd_kw)
    o.append('    {')
    o.append('        *Name: "%s"' % display)
    if code is not None:
        # rawtobr3_strings.txt 129-146 行原文: <1B>&l4096a<CODE>a6d1E (逐字节复制, 含常量 4096a/6d/1E)
        o.append('        *Command: CmdSelect')
        o.append('        {')
        o.append('            *Order: DOC_SETUP.%d' % ORDER["PaperSize"])
        o.append('            *Cmd: "<1B>&l4096a%da6d1E"' % code)
        o.append('        }')
        o.append('        *%% 纸型码: %s=%d (%s)' % (ppd_kw, code, conf))
    else:
        wu, hu = mm2units(w_mm), mm2units(h_mm)
        wd, hd = mm2pcl(w_mm), mm2pcl(h_mm)
        o.append('        *Command: CmdSelect')
        o.append('        {')
        o.append('            *Order: DOC_SETUP.%d' % ORDER["PaperSize"])
        o.append('            *Cmd: "<1B>&u600D<1B>*c%dX<1B>*c%dY<1B>*c0P"' % (wd, hd))
        o.append('        }')
        o.append('        *%% 无 rawtobr3 纸型码 → PCL5 标准自定义尺寸路由: %dx%d mm = %dx%d 点@600dpi (%s)' % (w_mm, h_mm, wd, hd, conf))
    dims = (mm2units(w_mm), mm2units(h_mm))
    o.append('        *PageDimensions: PAIR(%d, %d)' % dims)
    o.append('        *PrintableArea: PAIR(%d, %d)' % (dims[0] - 400, dims[1] - 400))
    o.append('        *PrintableOrigin: PAIR(200, 200)')
    o.append('        *% PPD *HWMargins 12pt → 200 master units')
    o.append('    }')
    return "\n".join(o)

def build_custom_option(gpd_kw, display, with_dynamic):
    """自定义尺寸选项(CustomMediaSize 动态 / CUSTOM1-3 预置槽动态).
    动态维度: %d{PhysPageWidth}/%d{PhysPageHeight}(Unidrv 命令参数; master units 假设 1200/in)。
    落机验证路径: 安装+测试页抓流; 参数名如不被解析器接受由安装测试暴露。"""
    wmin = mm2units(CUSTOM_MIN_MM[0]); hmin = mm2units(CUSTOM_MIN_MM[1])
    wmax = mm2units(CUSTOM_MAX_MM[0]); hmax = mm2units(CUSTOM_MAX_MM[1])
    o = []
    o.append('    *Option: %s' % gpd_kw)
    o.append('    {')
    o.append('        *Name: "%s"' % display)
    o.append('        *MinSize: PAIR(%d, %d)' % (wmin, hmin))
    o.append('        *MaxSize: PAIR(%d, %d)' % (wmax, hmax))
    o.append('        *MaxPrintableWidth: %d' % (wmax - 400))
    o.append('        *MinLeftMargin: 200')
    o.append('        *CenterPrintable?: FALSE')
    if with_dynamic:
        o.append('        *Command: CmdSelect')
        o.append('        {')
        o.append('            *Order: DOC_SETUP.%d' % ORDER["PaperSize"])
        o.append('            *Cmd: "<1B>&u1200D<1B>*c" %d{PhysPageWidth}"X<1B>*c" %d{PhysPageHeight}"Y<1B>*c0P"')
        o.append('        }')
        o.append('        *%% 自定义尺寸 %d-%d x %d-%d mm; *c0P=PCL5 custom(维度假设 master units@&u1200D, LOW 置信)' %
                 (CUSTOM_MIN_MM[0], CUSTOM_MAX_MM[0], CUSTOM_MIN_MM[1], CUSTOM_MAX_MM[1]))
    o.append('    }')
    return "\n".join(o)

def build_constraints(gpd_feature, gpd_option, pairs):
    """pairs: [(gpd_feature, gpd_option), ...] → *Constraints: LIST(...)"""
    if not pairs:
        return ""
    uniq = []
    for f, opt in pairs:
        ref = "%s.%s" % (f, opt)
        if ref not in uniq:
            uniq.append(ref)
    lines = ['    *%% UIConstraints → *Constraints(%d 条)' % len(uniq)]
    lines.append('        *Constraints: LIST(%s)' % ", ".join(uniq))
    return "\n".join(lines)

def convert_constraints(raw, paper_kw_set, duplex_kws, has_duplex, media_kws, inputbin_kws):
    """PPD UIConstraints 字符串列表 → {('Feat','Opt'): [('Feat','Opt'), ...]}"""
    cons = {}
    pat = re.compile(r'\*(\w+)\s+(\S+)\s+\*(\w+)\s+(\S+)')
    for c in raw or []:
        m = pat.match(c.strip())
        if not m:
            continue
        f1, o1, f2, o2 = m.groups()
        g1 = (CONSTRAINT_FEATURE_MAP.get(f1, f1), CONSTRAINT_NAME_MAP.get(o1, o1) if f1 == "PageSize" else o1)
        g2 = (CONSTRAINT_FEATURE_MAP.get(f2, f2), CONSTRAINT_NAME_MAP.get(o2, o2) if f2 == "PageSize" else o2)
        # 归一化 feature 名
        g1 = ("PaperSize", g1[1]) if f1 == "PageSize" else (g1[0], g1[1])
        g2 = ("PaperSize", g2[1]) if f2 == "PageSize" else (g2[0], g2[1])
        # 两侧都挂(PPD 语义对称; GPD LIST 约束在 UI 侧对称生效, 挂一侧即可, 这里按 PPD 第一个子句挂)
        # Duplex 不存在的机型丢弃 Duplex 约束
        if not has_duplex and (g1[0] == "Duplex" or g2[0] == "Duplex"):
            continue
        # 目标必须真实存在
        def valid(f, opt):
            if f == "PaperSize":  return opt in paper_kw_set
            if f == "MediaType":  return opt in media_kws
            if f == "InputBin":   return opt in inputbin_kws
            if f == "Duplex":     return opt in duplex_kws
            return False
        if valid(*g1) and valid(*g2):
            cons.setdefault(g1, []).append(g2)
    return cons

def generate_gpd(model, data, ppd_sizes, hw_margin_pt, defaults, feature_names, v3=False):
    """拼装单个型号的 GPD 全文. v3=True 时生成 v3 Unidrv 变体(去 *PrintSchemaPrivateNamespaceURI)."""
    name = model["ModelName"]
    token = name.replace(" ", "")
    gpd_name = token + ".gpd"
    has_duplex = bool(data.get("Duplex_opts"))
    has_sleep  = bool(data.get("Sleep_opts"))
    cons = convert_constraints(
        data.get("UIConstraints"),
        set([p[1] for p in PAPERS] + ["CUSTOM1", "CUSTOM2", "CUSTOM3", "CustomMediaSize"]),
        set([d[0] for d in DUPLEX]),
        has_duplex,
        set([m[0] for m in MEDIA]),
        set([i[0] for i in INPUTBIN]),
    )
    margin = mm2units(hw_margin_pt * 25.4 / 72.0)

    out = []
    out.append(GPD_HEADER_TPL.replace("@@MODEL@@", name).replace("@@GPD@@", gpd_name))
    if v3:
        # v3 Unidrv 不认识 v4 专属指令, 去掉整行(含前导注释分隔的该行)
        out[-1] = out[-1].replace('*PrintSchemaPrivateNamespaceURI: "http://www.lenovo.com/printing/woa/2024/LJ24"\n', '')

    # ---- Orientation (Unidrv 旋转栅格, 无设备命令; unishare/MXDW/GENIBM9 同构) ----
    out.append("""*Feature: Orientation
{
    *rcNameID: =ORIENTATION_DISPLAY
    *DefaultOption: PORTRAIT
    *Option: PORTRAIT
    {
        *rcNameID: =PORTRAIT_DISPLAY
    }
    *Option: LANDSCAPE_CC270
    {
        *rcNameID: =LANDSCAPE_DISPLAY
    }
}
""")

    # ---- InputBin (PJL SOURCETRAY, rawtobr3 44-50 行) ----
    ib_name = feature_names.get("InputSlot", "纸张来源")
    out.append("*Feature: InputBin\n{\n    *Name: \"%s\"\n    *DefaultOption: %s\n" %
               (ib_name, defaults.get("InputSlot", "TRAY1")))
    for kw, disp, pjl, note in INPUTBIN:
        pairs = cons.get(("InputBin", kw), [])
        out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
        out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["InputBin"])
        out.append("            *Cmd: \"%s\"\n        }\n" % gpd_cmd_escape("@PJL SET SOURCETRAY = %s\n" % pjl))
        out.append("        *%% SOURCETRAY: %s\n" % note)
        cb = build_constraints("InputBin", kw, pairs)
        if cb: out.append(cb + "\n")
        out.append("    }\n")
    out.append("}\n")

    # ---- MediaType (PJL MEDIATYPE, rawtobr3 65-73 行逐字节) ----
    mt_name = feature_names.get("BrMediaType", "介质类型")
    out.append("*Feature: MediaType\n{\n    *Name: \"%s\"\n    *DefaultOption: %s\n" %
               (mt_name, defaults.get("BrMediaType", "PLAIN")))
    for kw, disp, pjl_val in MEDIA:
        pairs = cons.get(("MediaType", kw), [])
        out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
        out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["MediaType"])
        out.append("            *Cmd: \"%s\"\n        }\n" % gpd_cmd_escape("@PJL SET MEDIATYPE = %s\n" % pjl_val))
        out.append("        *%% rawtobr3_strings.txt 65-73 行: @PJL SET MEDIATYPE = %s\n" % pjl_val)
        cb = build_constraints("MediaType", kw, pairs)
        if cb: out.append(cb + "\n")
        out.append("    }\n")
    out.append("}\n")

    # ---- Resolution (PJL 37-41 行 + PCL *t#R/&u#D 进 CmdBeginRaster) ----
    res_name = feature_names.get("Resolution", "分辨率")
    out.append("*Feature: Resolution\n{\n    *Name: \"%s\"\n    *DefaultOption: %s\n" %
               (res_name, defaults.get("Resolution", "600dpi")))
    for kw, disp, dx, dy, tdpi, pjl, pcl, note in RESOLUTIONS:
        out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
        out.append("        *DPI: PAIR(%d, %d)\n        *TextDPI: PAIR(%d, %d)\n        *SpotDiameter: 100\n" %
                   (dx, dy, dx, dy))
        out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["Resolution"])
        out.append("            *Cmd: \"%s\"\n        }\n" % gpd_cmd_escape(pjl))
        out.append("        *%% PJL: %s\n" % note)
        out.append("        *Command: CmdBeginRaster { *Cmd : \"%s<1B>*r0A<1B>*b0M\" }\n" % pcl)
        out.append("        *% rawtobr3=106 行 *r0A; 压缩显式 NONE *b0M(不发 1030M, brcomp1030 未还原)\n")
        out.append("    }\n")
    out.append("}\n")
    out.append("*Command: CmdEndRaster { *Cmd : \"<1B>*rB\" }\n")
    out.append("*% rawtobr3=107 行 *rB\n")
    out.append("*Command: CmdSendBlockData { *Cmd : \"<1B>*b\" %d{NumOfDataBytes}\"W\" }\n")
    out.append("*% unishare.gpd 同构; rawtobr3=108 行 *b1030m 为私有压缩, 不使用\n\n")

    # ---- PaperSize (原始 PPD 25 项 = 22 实纸型 + CUSTOM1-3, 加 CustomMediaSize) ----
    ps_name = feature_names.get("PageSize", "纸张大小")
    default_ps = defaults.get("PageSize", "ISOA4")
    out.append("*Feature: PaperSize\n{\n    *Name: \"%s\"\n    *DefaultOption: %s\n" % (ps_name, default_ps))
    ppd_display = dict((p[0], p[1]) for p in ppd_sizes)
    for ppd_kw, gpd_kw, w, h, code, conf in PAPERS:
        disp = ppd_display.get(ppd_kw, gpd_kw)
        out.append(build_paper_option(ppd_kw, gpd_kw, w, h, code, conf, disp) + "\n")
    for ck in ("CUSTOM1", "CUSTOM2", "CUSTOM3"):
        disp = ppd_display.get(ck, ck)
        out.append(build_custom_option(ck, disp, with_dynamic=True) + "\n")
    out.append(build_custom_option("CustomMediaSize", "Custom", with_dynamic=True) + "\n")
    out.append("}\n")

    # ---- Duplex (仅 20 款; rawtobr3 98-100 行) ----
    if has_duplex:
        dx_name = feature_names.get("Duplex", None)
        if dx_name:
            out.append("*Feature: Duplex\n{\n    *Name: \"%s\"\n" % dx_name)
        else:
            out.append("*Feature: Duplex\n{\n    *rcNameID: =TWO_SIDED_PRINTING_DISPLAY\n")
        out.append("    *DefaultOption: OneSided\n")
        for kw, disp, scode, note in DUPLEX:
            pairs = cons.get(("Duplex", kw), [])
            out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
            out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["Duplex"])
            out.append("            *Cmd: \"<1B>&l%dS\"\n        }\n" % scode)
            out.append("        *%% %s\n" % note)
            cb = build_constraints("Duplex", kw, pairs)
            if cb: out.append(cb + "\n")
            out.append("    }\n")
        out.append("}\n")

    # ---- TonerSave (rawtobr3 42/43 行, 自检逐字节比对) ----
    ts_name = feature_names.get("TonerSave", "省墨模式")
    out.append("*Feature: TonerSave\n{\n    *Name: \"%s\"\n    *DefaultOption: %s\n" %
               (ts_name, defaults.get("TonerSave", "OFF")))
    for kw, disp, pjl, note in TONER:
        out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
        out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["TonerSave"])
        out.append("            *Cmd: \"%s\"\n        }\n" % gpd_cmd_escape(pjl))
        out.append("        *%% %s\n" % note)
        out.append("    }\n")
    out.append("}\n")

    # ---- Sleep (rawtobr3 83 行前缀 + 值; PRINTER=默认不发) ----
    if has_sleep:
        sl_name = feature_names.get("Sleep", "休眠时间[分]")
        out.append("*Feature: Sleep\n{\n    *Name: \"%s\"\n    *DefaultOption: PRINTER\n" % sl_name)
        for kw, disp, val in SLEEP:
            out.append("    *Option: %s\n    {\n        *Name: \"%s\"\n" % (kw, disp))
            if val is not None:
                out.append("        *Command: CmdSelect\n        {\n            *Order: DOC_SETUP.%d\n" % ORDER["Sleep"])
                out.append("            *Cmd: \"%s\"\n        }\n" % gpd_cmd_escape("@PJL SET AUTOSLEEP=%d\n" % val))
                out.append("        *% rawtobr3=83 行 \"@PJL SET AUTOSLEEP=\" 前缀 + 动态值(MEDIUM 置信)\n")
            else:
                out.append("        *% 设备默认, 不发命令\n")
            out.append("    }\n")
        out.append("}\n")

    # ---- ColorMode (单色 1bpp; 无设备命令) ----
    out.append("""*Feature: ColorMode
{
    *rcNameID: =COLOR_PRINTING_MODE_DISPLAY
    *DefaultOption: Mono
    *Option: Mono
    {
        *Name: "黑白"
        *DevBPP: 1
        *DevNumOfPlanes: 1
        *DrvBPP: 8
    }
}
""")

    # ---- Halftone (8bpp→1bpp 抖动; GENIBM9 同构) ----
    out.append("""*Feature: Halftone
{
    *rcNameID: =HALFTONING_DISPLAY
    *DefaultOption: HT_PATSIZE_AUTO
    *Option: HT_PATSIZE_AUTO
    {
        *rcNameID: =HT_AUTO_SELECT_DISPLAY
    }
    *Option: HT_PATSIZE_6x6_M
    {
        *rcNameID: =HT_DITHER6X6_DISPLAY
    }
    *Option: HT_PATSIZE_8x8_M
    {
        *rcNameID: =HT_DITHER8X8_DISPLAY
    }
}
""")

    # ---- 全局命令/属性 (纯文本, @@TOKEN@@ 填充, 避开 %-format 与字面 %% 冲突) ----
    out.append("""*Command: CmdStartJob
{
    *Order: JOB_SETUP.1
    *Cmd : "@@STARTJOB@@"
}
*% rawtobr3=30 行 UEL+@PJL, 31 行 @PJL JOB NAME="Linux print job"\\n(LF; 任务书稿写 \\r\\n 以 strings 为准)
*Command: CmdStartDoc
{
    *Order: DOC_SETUP.@@DOCORDER@@
    *Cmd : "@@STARTDOC@@"
}
*% rawtobr3=80 行; *Order 把 ENTER LANGUAGE=PCL 编排到 PJL SET 之后、PCL 命令之前
*Command: CmdEndJob
{
    *Order: JOB_FINISH.1
    *Cmd : "@@ENDJOB@@"
}
*% rawtobr3=32 行 EOJ + 33 行 UEL; *Order: JOB_FINISH.1 必需——unidrv 只执行带 *Order 的命令, 缺失则 EOJ/收尾 UEL 从不发出(运行期实测实锤)
*Command: CmdCR { *Cmd : "<0D>" }
*Command: CmdLF { *Cmd : "<0A>" }
*Command: CmdFF { *Cmd : "<0C>" }
*EjectPageWithFF?: TRUE
*% rawtobr3=105 行 \\f 页结束; 页起不再发命令(FF 后光标回页首)
*CursorXAfterSendBlockData: AT_GRXDATA_START
*CursorYAfterSendBlockData: NO_MOVE
*OutputDataFormat: H_BYTE
*% PCL5 栅格: 行数据 *b#W 自动推进 Y, X 回行首
""".replace("@@STARTJOB@@", CMD_START_JOB)
       .replace("@@STARTDOC@@", CMD_START_DOC)
       .replace("@@ENDJOB@@", CMD_END_JOB)
       .replace("@@DOCORDER@@", str(DOC_ORDER)))
    return "\n".join(out), gpd_name, token

def main():
    os.makedirs(DRIVER, exist_ok=True)
    os.makedirs(BUILD, exist_ok=True)
    with open(PPDJSON, "r", encoding="utf-8") as f:
        models = json.load(f)
    assert isinstance(models, list) and len(models) == 27, "ppd_extract.json 应为 27 元素数组"

    # --v3 模式: 只生成 LJ2405D 的 v3 Unidrv 变体 GPD → build\v3\ (用于 AddPrinterDriverEx 运行期验证)
    if "--v3" in sys.argv:
        v3dir = os.path.join(BUILD, "v3")
        os.makedirs(v3dir, exist_ok=True)
        ppd_files = sorted(_glob.glob(PPD_GLOB))
        sizes = []
        pat = re.compile(r'\*PageSize\s+(\S+?)\s*/\s*([^:]*?):\s*"([^"]*)"')
        hw_margin_pt = 12.0
        default_ppd_ps = None
        with open(ppd_files[0], "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat.match(line)
                if m:
                    sizes.append((m.group(1), m.group(2).strip()))
                    continue
                m2 = re.match(r'\*DefaultPageSize:\s+(\S+)', line)
                if m2:
                    default_ppd_ps = m2.group(1)
                m3 = re.match(r'\*HWMargins:\s+([\d.]+)', line)
                if m3:
                    hw_margin_pt = float(m3.group(1))
        m = [x for x in models if x["ModelName"] == "LJ2405D"][0]
        defaults = {
            "PageSize": CONSTRAINT_NAME_MAP.get(default_ppd_ps, default_ppd_ps),
            "Resolution": m.get("DefaultResolution", "600dpi"),
            "BrMediaType": m.get("DefaultBrMediaType", "PLAIN"),
            "InputSlot": m.get("DefaultInputSlot", "TRAY1"),
            "TonerSave": m.get("DefaultTonerSaveMode", "OFF"),
        }
        def feat_name_v3(data, key):
            ou = data.get("OpenUI") or []
            want = key.lower().replace("_", "")
            for item in ou:
                if isinstance(item, dict):
                    nm = str(item.get("name", "")).replace("*", "").replace("_", "").lower()
                    if nm == want or nm.startswith(want):
                        return item.get("trans")
            return None
        fns = {
            "PageSize": feat_name_v3(m, "PageSize") or "纸张大小",
            "BrMediaType": feat_name_v3(m, "BrMediaType") or "介质类型",
            "InputSlot": feat_name_v3(m, "InputSlot") or "纸张来源",
            "Resolution": feat_name_v3(m, "Resolution") or "分辨率",
            "TonerSave": feat_name_v3(m, "TonerSave") or "省墨模式",
            "Sleep": feat_name_v3(m, "Sleep") or "休眠时间[分]",
            "Duplex": feat_name_v3(m, "Duplex"),
        }
        text, gpd_name, token = generate_gpd(m, m, sizes, hw_margin_pt, defaults, fns, v3=True)
        with open(os.path.join(v3dir, gpd_name), "wb") as f:
            f.write(text.encode("utf-16"))
        print("OK v3:", os.path.join(v3dir, gpd_name))
        return

    # 原始 PPD: PageSize 25 项 + DefaultPageSize + HWMargins
    ppd_files = sorted(_glob.glob(PPD_GLOB))
    assert ppd_files, "未找到原始 PPD: " + PPD_GLOB
    sizes = []
    hw_margin_pt = 12.0
    default_ppd_ps = None
    pat = re.compile(r'\*PageSize\s+(\S+?)\s*/\s*([^:]*?):\s*"([^"]*)"')
    with open(ppd_files[0], "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.match(line)
            if m:
                sizes.append((m.group(1), m.group(2).strip()))
                continue
            m2 = re.match(r'\*DefaultPageSize:\s+(\S+)', line)
            if m2:
                default_ppd_ps = m2.group(1)
            m3 = re.match(r'\*HWMargins:\s+([\d.]+)', line)
            if m3:
                hw_margin_pt = float(m3.group(1))
    assert len(sizes) == 25, "原始 PPD PageSize 应为 25 项, 实得 %d" % len(sizes)
    assert default_ppd_ps == "A4", "DefaultPageSize=%s (预期 A4)" % default_ppd_ps

    # PrinterDriverID: 固定种子 uuid4 ×27, 可复现
    random.seed(20240501)
    guids = []
    for _ in range(len(models)):
        u = uuid.UUID(int=random.getrandbits(128), version=4)
        guids.append("{" + str(u).upper() + "}")

    # OpenUI 中文名: JSON 结构为 [{"name":"*PageSize","trans":"纸张大小",...}, ...]
    def feat_name(data, key):
        ou = data.get("OpenUI") or []
        want = key.lower().replace("_", "")
        for item in ou:
            if not isinstance(item, dict):
                continue
            nm = str(item.get("name", "")).replace("*", "").replace("_", "").lower()
            if nm == want or nm.startswith(want):
                return item.get("trans")
        return None

    info = []   # (token, guid, usb_id or None)
    for idx, m in enumerate(models):
        name = m["ModelName"]
        token = name.replace(" ", "")
        defaults = {
            "PageSize":  CONSTRAINT_NAME_MAP.get(default_ppd_ps, default_ppd_ps),
            "Resolution": m.get("DefaultResolution", "600dpi"),
            "BrMediaType": m.get("DefaultBrMediaType", "PLAIN"),
            "InputSlot": m.get("DefaultInputSlot", "TRAY1"),
            "TonerSave": m.get("DefaultTonerSaveMode", "OFF"),
        }
        fns = {
            "PageSize":    feat_name(m, "PageSize") or "纸张大小",
            "BrMediaType": feat_name(m, "BrMediaType") or "介质类型",
            "InputSlot":   feat_name(m, "InputSlot") or "纸张来源",
            "Resolution":  feat_name(m, "Resolution") or "分辨率",
            "TonerSave":   feat_name(m, "TonerSave") or "省墨模式",
            "Sleep":       feat_name(m, "Sleep") or "休眠时间[分]",
            "Duplex":      feat_name(m, "Duplex"),
        }
        gpd_text, gpd_name, token = generate_gpd(m, m, sizes, hw_margin_pt, defaults, fns)
        # GPD: UTF-16 LE BOM
        with open(os.path.join(DRIVER, gpd_name), "wb") as f:
            f.write(gpd_text.encode("utf-16"))
        # manifest
        manifest = ("[DriverConfig]\r\n"
                    "DataFile=%s\r\n"
                    "RequiredFiles=UNIRES.DLL,STDNAMES.GPD,STDDTYPE.GDL,STDSCHEM.GDL,STDSCHMX.GDL,MSXPSINC.GPD\r\n"
                    "PrinterDriverID=%s\r\n"
                    "DriverCategory=PrintFax.Printer\r\n"
                    "\r\n"
                    "[DriverRender]\r\n"
                    "XpsFormat=OpenXPS,XPS\r\n" % (gpd_name, guids[idx]))
        with open(os.path.join(DRIVER, token + "-manifest.ini"), "wb") as f:
            f.write(manifest.encode("ascii"))
        # pipelineconfig(与 unishare-pipelineconfig.xml 逐字节一致的内容)
        pc = '<?xml version="1.0" encoding="utf-8"?>\n<Filters />'
        with open(os.path.join(DRIVER, token + "-pipelineconfig.xml"), "wb") as f:
            f.write(pc.encode("utf-8"))
        usb = USB_IDS.get(token)
        info.append((token, guids[idx], usb))

    # ---------- INF ----------
    L = []
    L.append("; Lenovo LJ24/LJ26/M74/M76 全系列 WoA v4 打印驱动 (纯数据 Unidrv 包)")
    L.append("; 由 gen_gpd.py 生成; 结构对齐: prnms001.Inf(MXDW)+LEXHL13A.INF(Brother v4)")
    L.append("")
    L.append("[Version]")
    L.append('Signature="$Windows NT$"')
    L.append("Provider=%Provider%")
    L.append("ClassGUID={4D36E979-E325-11CE-BFC1-08002BE10318}")
    L.append("Class=Printer")
    L.append("ClassVer=4.0")
    L.append("DriverVer=01/01/2025,1.0.0.0")
    L.append("DriverIsolation=2")
    L.append("CatalogFile.NTamd64 = LJ2400WOA_amd64.cat")
    L.append("CatalogFile.NTarm64 = LJ2400WOA_arm64.cat")
    L.append("")
    L.append("[Manufacturer]")
    L.append("%Provider%=Lenovo, NTarm64.6.0, NTamd64.6.0, NTx86.6.0")
    for decor in ("NTarm64.6.0", "NTamd64.6.0", "NTx86.6.0"):
        L.append("")
        L.append("[Lenovo.%s]" % decor)
        for i, (token, guid, usb) in enumerate(info):
            ids = ["{%s}" % guid.strip("{}")]
            if usb:
                ids += [usb, usb.split("\\", 1)[1]]
            L.append("%%Model.%d%% = %s.Install, %s" % (i + 1, token, ",".join(ids)))
    L.append("")
    for token, _, _ in info:
        L.append("[%s.Install]" % token)
        L.append("CopyFiles=DriverFiles")
        L.append("")
    L.append("[DriverFiles]")
    for token, _, _ in info:
        L.append("%s.gpd" % token)
        L.append("%s-manifest.ini" % token)
        L.append("%s-pipelineconfig.xml" % token)
    L.append("")
    L.append("[DestinationDirs]")
    L.append("DefaultDestDir=66000")
    L.append("")
    L.append("[SourceDisksNames]")
    L.append("1=%Disk1%,,,")
    L.append("")
    L.append("[SourceDisksFiles]")
    for token, _, _ in info:
        L.append("%s.gpd=1" % token)
        L.append("%s-manifest.ini=1" % token)
        L.append("%s-pipelineconfig.xml=1" % token)
    L.append("")
    L.append("[Strings]")
    L.append('Provider = "%s"' % PROVIDER)
    L.append('Disk1 = "%s"' % DISK1)
    for i, m in enumerate(models):
        L.append('Model.%d = "Lenovo %s"' % (i + 1, m["ModelName"]))
    inf_text = "\r\n".join(L) + "\r\n"
    with open(os.path.join(DRIVER, INF_NAME), "wb") as f:
        f.write(inf_text.encode("utf-16"))

    # 元数据供自检使用
    meta = {
        "models": [m["ModelName"] for m in models],
        "guids": guids,
        "usb": USB_IDS,
        "papers": [[p[0], p[1], p[2], p[3], p[4]] for p in PAPERS],
        "default_ppd_pagesize": default_ppd_ps,
        "strings_file": STRINGS,
        "orders": ORDER, "doc_order": DOC_ORDER,
    }
    with open(os.path.join(BUILD, "gen_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("OK: 27 GPD + 27 manifest + 27 pipelineconfig + INF ->", DRIVER)
    print("DefaultPageSize:", default_ppd_ps, "HWMargins(pt):", hw_margin_pt, "PageSize options:", len(sizes))

if __name__ == "__main__":
    main()
