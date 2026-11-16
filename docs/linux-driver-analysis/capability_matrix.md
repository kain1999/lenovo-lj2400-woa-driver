# Lenovo LJ24/LJ26/M74/M76 系列 Linux 打印驱动 — 全系列能力矩阵与命令协议

> 样本：`signed_com.lenovo.lenovoprints_5.0.3-2_amd64.deb`（UOS）+ `com.lenovo.lenovoprints_5.0.3-2_amd64.deb`（麒麟V10）
> 解包产物：`E:\Deepseek\lj2400lin\deb_extract\{uos_print,kylin_print,uos_scan}`；逐字段提取：`ppd_extract.json` / `ppd_extract.txt`
> 用途：为 Windows on ARM 驱动提供全系列能力矩阵与命令层依据。所有结论均有 文件:行号 级证据。

---

## 1. 结论先行

- **全系列 27 机型是同一个协议家族**：deb 内只有一套转换器（三架构各两份 ELF：`rawtobr3`、`brprintconflsr3`），机型差异全部参数化（PPD `BrPrinterType` 注释 + `brlenovoprintsrc` rc 默认值）。
- **命令协议 = UEL(`ESC %-12345X`) + PJL(Brother 扩展 SET) + PCL5 光栅（Brother 私有 `ESC *b1030M` 压缩）**。PPD 里没有 @PJL（PS 直通型 PPD），PJL 在 rawtobr3 输出层注入。
- **CUPS filter 是 perl 脚本**（`lpdwrapper`，postinst 软链 27 次），不是 ELF；栅格化靠 Ghostscript `-sDEVICE=bit`，真正协议生成靠 `rawtobr3` ELF。
- **省墨**：PPD 名 `*TonerSaveMode`（命令原文 `statusdict begin true/false tonersave end`）；设备侧真名 `@PJL SET ECONOMODE = ON/OFF`。27/27 全支持。
- **双面**：27 款中 7 款无（NTM24 组），20 款有（DuplexTumble/DuplexNoTumble/None）。
- **UOS 与麒麟包内容 36/42 文件逐字节一致**，仅 6 个 ELF 多一个 deepin `.sig` 签名段；能力与协议零差异。

## 2. deb 结构与安装（问题1）

| 项 | 值 | 证据 |
|---|---|---|
| ar 成员 | debian-binary / control.tar.gz / data.tar.xz / sign / sign.tar.gz（UOS 多后两个） | `unpack_manifest.json` |
| control 依赖 | `Depends: deepin-elf-verify`（UOS）；描述 "printer driver (lpd/cups)"；Installed-Size 672 | `uos_print\control.tar.gz.d\._control:7` |
| PPD 落点 | `/usr/share/cups/model/lenovo/lenovo-<MODEL>-cups-en.ppd` ×27 | `data.tar.xz.d\._usr_share_cups_model_lenovo_*` |
| CUPS filter | **perl 脚本** `cupswrapper/lpdwrapper`，postinst 软链到 `/usr/lib{,32,64}/cups/filter/` 与 `/usr/libexec/cups/filter/` 下 `lenovo_<MODEL>` | `._postinst:48-60`；lpdwrapper:1 `#! /usr/bin/perl` |
| ELF 二进制 | `lpd/{x86_64,aarch64,mips64}/{rawtobr3, brprintconflsr3}` 6 个；无 udev 规则 | `classify.py` 输出 |
| 安装脚本 | postinst：按 `uname -m` 软链 rawtobr3/brprintconflsr3、每机型生成 `/usr/bin/brprintconflsr3_<MODEL>` 包装、建 CUPS filter 软链；prerm：清理 + SELinux semanage；postrm：重启 lprng/lpd | `._postinst/. _prerm/. _postrm` 全文 |
| 其它运行时依赖 | perl（postinst 检查并告警）、ghostscript（lpdfilter 调 gs）、brprintconflsr3 写 rc 需 `/etc/opt/lenovo/...` 目录 | `._postinst:26-37`；lpdfilter:224 |
| 扫描驱动 deb | 22 文件纯 SANE 栈（libsane-lenovo3 等 5 ELF + udev rules + models ini），**不含打印组件** | `classify.py` uos_scan 段 |

## 3. 渲染管线与命令协议（问题3）

```
CUPS ──PS/PDF──▶ lenovo_<MODEL>（= lpdwrapper perl，软链）
                    │  解析 PPD *Default* 行 + CUPS 选项
                    │  逐项执行： brprintconflsr3 -P <MODEL> -res|-ps|-pt|-md|-dx|-dxt|-ob|-sp|-ts|-cp <val>
                    │            （写入临时 rc 文件，$ENV{BRPRINTERRCFILE}）
                    ▼
                 lpdfilter (perl, ENV{PS}=1)
                    │  读 rc 的 Resolution/PaperType
                    │  纸型→600dpi 点数：内置 PAPERTBL 23 项 或 BRPAPERWIDTH/HEIGHT 环境变量（自定义纸）
                    ▼
                 gs -r<res> -g<WxH> -q -dNOPAUSE -dSAFER -sDEVICE=bit -sOutputFile=-   （PS/PDF→raw bits）
                    ▼
                 rawtobr3 -rc <rc> -flags <flags1> -offset <offset> -ps <WxH>          （ELF，stdin→stdout .prn）
                    ▼  输出协议：
   ESC %-12345X @PJL            ← UEL
   @PJL JOB NAME="Linux print job"
   @PJL SET RESOLUTION = 300|600|1200
   @PJL SET RAS1200MODE = TRUE|ON|OFF          (Brother 1200dpi 光栅模式)
   @PJL SET PAPERFEEDSPEED = HALF|FULL         (1200 时)
   @PJL SET ECONOMODE = ON|OFF                 ← 省墨的设备侧真名
   @PJL SET SOURCETRAY = TRAY1..TRAY5|MPTRAY|AUTO
   @PJL SET OUTBIN = AUTO|UPPER|ALLSORTER|ALLSTACKER|OPTIONAL|OPTIONALOUTPUTBIN1..4
   @PJL SET COPY = n
   @PJL SET MEDIATYPE = REGULAR|THIN|THICK|THICK2|TRANSPARENCY|ENVELOPES|ENVTHICK|ENVTHIN|RECYCLED
   @PJL SET HQMMODE = ON|OFF                   ← HQ1200
   @PJL SET ORIENTATION = PORTRAIT / @PJL SET PAPER = ... / @PJL SET RIGHTMARGIN = 78 / @PJL SET PAGEPROTECT = AUTO
   @PJL SET|DEFAULT AUTOSLEEP= / TIMEOUTSLEEP= ← Sleep 落点
   @PJL SET USERNAME= / LOGINUSER= / HOLDKEY= / JOBNAME= / HOLD=STORE / HOLDTYPE=PRIVATE   ← 安全打印
   @PJL ENTER LANGUAGE = PCL
   PCL5: ESC *t150R|300R|600R|1200R   （光栅分辨率）
         ESC &l0S|1S|2S               （simplex / 长边装订 / 短边装订 ← duplex 落点）
         ESC &l1H|2H|1001H            （纸源选择）
         ESC &u300D|600D|1200D|150D   （unit of measure）
         ESC *r0A ... ESC *b1030M ... ESC *rB  （光栅起止 + Brother 私有压缩模式 1030M，导出函数 brcomp1030）
         ESC &l0E / FF ESC &l5.4C ESC &l1E    （页边界）
   @PJL EOJ NAME="Linux print job"
```

证据：`analysis\rawtobr3_strings.txt`（iz 全量，0x9461–0xba3c）；rawtobr3 导出表 `brcomp1030`/`PCLSetMargins`/`PCLCompressMode9`/`PJLSetMargin_A4`/`matrix600`（512B 抖动矩阵）；lpdwrapper:119-198/342-363/826-842；lpdfilter:13-41/107-117/224-268；rawtobr3 main（`analysis\rawtobr3_main.asm`，3854B @0x26af）参数 `-func/-offset/-flags/-ps WxH/-owner/-nodename/-password/-jobname/-enable-euf` + 环境变量 `OWNER/PASSWORD/TITLE/NODENAME/CHARSET(UTF-8/EUC-CN/JP/KR/TW 转码)`。

**选项映射表**（lpdwrapper `vendor_commandline` / `initial_configuration`，命令层入口即 Windows 移植的参数协议）：

| 语义 | wrapper 参数 | 取值 |
|---|---|---|
| 分辨率 | `-res` | 300 / 600 / 600x300 / 1200 / HQ1200 / HQ1200A(=1200x600) / HQ1200B(=2400x600) |
| 纸源 | `-ps` | MANUAL / MP / T1..T5 / AUTO |
| 纸型 | `-pt` | A4 LT LGL EXE A5 A6 JISB5 B5 JISB6 B6 C5 DL COM-10 MONARCH PC4X6 POSTCARD DHAGAKI ENVYOU4 ENVCHOU3 ENVCHOU4 3X5 FOLIO A4L 195x270mm 184x260mm 197x273mm CUSTOM0..9 |
| 介质 | `-md` | PLAIN THIN THICK THICKER BOND TRANS ENV ENV-THICK ENV-THIN RECYCLED |
| 双面 | `-dx` + `-dxt` | ON/OFF + LONG/SHORT |
| 出纸 | `-ob` | AUTO SB OB1-4 STC SRT2-5 OPT |
| 休眠 | `-sp` | PRINTER / 2 / 10 / 30 |
| 省墨 | `-ts` | OFF / ON |
| 份数 | `-cp` | 1.. |
| 密码 | `ENV{PASSWORD}` | 4 位数字（rawtobr3 `-password`） |
| 自定义纸尺寸 | `BRPAPERWIDTH/BRPAPERHEIGHT` | 600dpi 点数（pt×600/72，mm×6000/254，in×600） |

## 4. PPD 能力基线（全系列公共项）

- 分辨率：`*DefaultResolution: 600dpi`；选项 `{300dpi, 600dpi, 2400x600dpi/HQ1200}`（PPD 名）→ wrapper `HQ1200B`（27/27 相同）
- 灰度：`*ColorDevice: False`、`*DefaultColorSpace: Gray`
- 介质：`*BrMediaType` 9 种 PLAIN/THIN/THICK/THICKERPAPER2/BOND/ENV/ENVTHICK/ENVTHIN/RECYCLED
- 纸源：`*InputSlot` 仅 `{MANUAL 手动, TRAY1 纸盒1}`
- 纸型：20 种 PageSize（Letter/Legal/Executive/Folio/A4/A5/A6/Com-10/Monarch/DL/C5/ISOB5/JISB5/ISOB6/JISB6/4x6/明信片/双明信片/Y4信封/16K×3 规格）+ CUSTOM1/2/3 预置自定义位
- 自定义纸：`*VariablePaperSize: True`，宽 76.2–215.9mm、高 127–355.6mm
- 省墨：`*TonerSaveMode` OFF/ON → `statusdict begin {false|true} tonersave end`（PPD 层原文）
- 休眠：`*Sleep` PrinterDefault/2/10/30 → `statusdict begin N powersavetime end`（仅部分机型有此 UI）
- cupsModelNumber 全部 =72，`BrCustomPaperSize: TRUE`

## 5. 27 机型能力矩阵（问题6；BrPrinterType 为 PPD:8 注释编码）

| # | 型号 | BrPrinterType | 双面 | 省墨 | Sleep UI | 分辨率 | 介质/纸源 | UICon |
|---|------|--------------|------|------|---------|--------|-----------|-------|
| 1 | LJ2400Pro | NTM24 | — | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 4 |
| 2 | LJ2405 | NTM24 | — | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 4 |
| 3 | LJ2405D | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 4 | LJ2605D | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 5 | LJ2655DN | ENAHQ1200ADTMSLEEPEND | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 60 |
| 6 | LJ2680DN | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 7 | M7400Pro | NTM24 | — | ✓ | — | 300/600/HQ1200 | 9/2 | 4 |
| 8 | M7400W | NTM24 | — | ✓ | — | 300/600/HQ1200 | 9/2 | 4 |
| 9 | M7405D | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 10 | M7405DW | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 11 | M7450FPro | NTM24 | — | ✓ | — | 300/600/HQ1200 | 9/2 | 4 |
| 12 | M7455DNF | ENAHQ1200ADTMSCANEND | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 60 |
| 13 | M7460 | NTM24 | — | ✓ | — | 300/600/HQ1200 | 9/2 | 4 |
| 14 | M7480 | NTM24 | — | ✓ | — | 300/600/HQ1200 | 9/2 | 4 |
| 15 | M7490DNF | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 16 | M7605D | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 17 | M7605DW | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 18 | M7615DNA | ENAHQ1200ADTMSCANEND | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 60 |
| 19 | M7625DWA | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 20 | M7626DNA | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 21 | M7628DNA | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 22 | M7655DHF | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 23 | M7675DXF | ENAHQ1200ADTMSCANEND | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 60 |
| 24 | M7680D | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |
| 25 | M7685DXF | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 26 | M7686DXF | DTM | ✓ | ✓ | — | 300/600/HQ1200 | 9/2 | 12 |
| 27 | M7690DNA | DTM | ✓ | ✓ | ✓ | 300/600/HQ1200 | 9/2 | 12 |

命令语言（全系列统一）：**UEL + PJL(Brother 扩展) + PCL5 光栅 + ESC*b1030M 压缩**，灰度位图，300/600/1200dpi（HQ1200B=2400x600 逻辑分辨率，实际 gs 按 1200 栅格 ×2 尺寸）。
注：适配机型.txt 26 名单中 `lenovo-L2405-cups-en.ppd` 在 deb 中实际为 `LJ2405`；deb 共 27 个 PPD（26 + LJ2405）。
BrPrinterType 编码释义（静态推断，置信度 medium）：N=No duplex / D=Duplex / T=Twin?（Tray1）/ M=?；ENA=Enab HQ1200、ADTMSLEEPEND/ADTMSCANEND 含 duplex+Sleep/Scan(fax) 能力位。

## 6. LJ2400Pro vs LJ2655DN 差异表（问题5）

| 能力 | LJ2400Pro | LJ2655DN |
|------|-----------|----------|
| BrPrinterType | NTM24 | ENAHQ1200ADTMSLEEPEND |
| Duplex OpenUI | **无**（仅注释占位 `*%=== Duplex ===`） | **有**：None/DuplexNoTumble(长边)/DuplexTumble(短边) |
| UIConstraints | 4 条（TRAY1 vs Custom/CUSTOM1-3） | 60 条（duplex × 17 纸型/介质排除 + TRAY1 约束） |
| 省墨 | ✓ TonerSaveMode | ✓ TonerSaveMode |
| 分辨率 | 300/600/HQ1200 | 300/600/HQ1200（同） |
| Sleep UI | ✓（2/10/30 min + powersavetime） | ✓ |
| 介质/纸源/纸型 | 9/2/20 | 9/2/20（同） |
| 命令语言 | 同一 rawtobr3 → 同一 PJL/PCL 协议 | 同左 |
| 体积 | 14218B | 17661B（增量全在 Duplex UI + 60 条约束） |

## 7. 五机型命令层抽检（问题4：LJ2400Pro/L2405D/LJ2655DN/M7405DW/M7615DNA）

| 项 | LJ2400Pro | L2405D | LJ2655DN | M7405DW | M7615DNA |
|---|---|---|---|---|---|
| cupsFilter | PS 0 lenovo_LJ2400Pro + PDF | 同构 lenovo_L2405D | 同构 lenovo_LJ2655DN | 同构 lenovo_M7405DW | 同构 lenovo_M7615DNA |
| JCLBegin/JCLToPDFInterpreter/JCLEnd | 无 | 无 | 无 | 无 | 无 |
| @PJL 出现次数(PPD 内) | 0 | 0 | 0 | 0 | 0 |
| statusdict 命令集 | tonersave×2 + powersavetime×3 | 同 | 同 | tonersave×2（无 powersavetime） | tonersave×2 |
| Duplex OpenUI | 无 | 有(3 选项) | 有(3 选项) | 有(3 选项) | 有(3 选项) |
| 初始配置（wrapper initial_configuration） | -res600 -psAUTO -obAUTO -dxOFF -dxtLONG -ptA4 -mdPLAIN -cp1 -spPRINTER -tsOFF（五机型全同，单一 lpdwrapper 服务全部机型） | | | | |

**判定：全系列同一 raster/PCL 协议家族**（同一 rawtobr3 二进制、同一 PJL/PCL 命令集、同一 rc 参数域），机型差异只是 rc 默认值与 PPD UI 集合的裁剪。Windows 驱动可做成**单一渲染引擎 + 机型能力表**。

## 8. Windows on ARM 移植要点

1. 输入侧直接接收 XPS/PDF→转 PS 或直接栅格化为 600/1200dpi 灰度位图，跳过 gs；原始管线 = gs bit 设备 600dpi raw bits（msb-first 行序，宽高点数见 PAPERTBL）。
2. 打包器需实现：UEL+PJL 头（上表 SET 项按能力表裁剪）→ PCL5 光栅（`*r0A`…`*b1030M`…`*rB`，1030M 行压缩算法在 brcomp1030，需进一步反汇编还原）→ `*rB`/FF/EOJ。
3. 纸型表直接复用 lpdfilter PAPERTBL 的 600dpi 点数（A4=4961×7016 等 23 项）+ 16K 三规格。
4. duplex/省墨/介质映射：`&l1S/2S` ↔ 长边/短边；`ECONOMODE` ↔ 省墨；`MEDIATYPE` ↔ 介质。
5. HQ1200B(2400×600) 是逻辑名：实际栅格 1200dpi + `@PJL SET RAS1200MODE=TRUE` + `PAPERFEEDSPEED`。
6. 安全打印为可选：PJL HOLD=STORE/HOLDTYPE=PRIVATE/HOLDKEY（4 位数字）。

## 9. 证据文件清单

| 文件 | 内容 |
|---|---|
| `deb_extract\unpack_manifest.json` | 三个 deb 的 ar 成员与 46/46/22 文件清单+哈希 |
| `deb_extract\{uos_print,kylin_print,uos_scan}\` | 解包产物（保持安装路径结构） |
| `analysis\ppd_extract.json` / `ppd_extract.txt` | 27 PPD 逐字段（分辨率/duplex/省墨/介质/纸源/纸型/UIConstraints/cupsFilter/JCL） |
| `analysis\rawtobr3_strings.txt` | rawtobr3 473 条字符串（完整 PJL/PCL 命令原文） |
| `analysis\rawtobr3_main.asm` | rawtobr3 main 反汇编（参数解析） |
| `analysis\diff_uos_kylin.py` | UOS vs 麒麟逐文件 SHA256 diff 脚本 |
| `analysis\extract_ppd.py` / `matrix.py` / `classify.py` | 提取/矩阵/类型判定脚本（可复跑） |

## 10. 局限与下一步（如实记录）

- `brcomp1030`（ESC*b1030M 行压缩）与 `matrix600`（512B 抖动矩阵）的字节级算法未反汇编还原——需对 rawtobr3 .text 深挖（本任务只到字符串/导出层）。
- `flags1=0000000000000500` 的位含义（rawtobr3 -flags 分支）未逐位核对，结论标注 medium。
- PPD 层 `statusdict tonersave/powersavetime` 命令只在 PS 直通路径有意义；CUPS 管线实际生效路径是 `-ts/-sp → rc → rawtobr3 → PJL ECONOMODE/AUTOSLEEP`。
- LJ2655DN 的 ENAHQ1200ADTMSLEEPEND 与 M7455DNF 的 SCANEND 后缀语义（Sleep/Scan 能力位）为静态推断。
