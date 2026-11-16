# Lenovo LJ2655DN (Brother OEM) GDI/XPS 驱动功能定义与型号差异矩阵
来源：install\driver\gdi\32_64\LEPRM13A.DSI（系列主配置）、LESHLJ*.DSI（型号覆盖）、xmlpaper\32_64\LEXM13A.DSI + LEXSHLJ*.DSI
行号引用以文件原文为准。

## 功能定义位置总表
| 功能 | 定义文件 | 关键键 | 命令层（渲染时输出） |
| --- | --- | --- | --- |
| 纸张尺寸 | LEPRM13A.DSI [PaperSize] L4-34 | 枚举→DEVMODE 码 | [PaperSize_Command] L91-121: ESC &l#a6d1E（如 A4=\x1b&l26a6d1E） |
| 介质类型 | LEPRM13A.DSI [MediaType] L35-48 | Plain/Thin/Thick/.../Label | leenm13a.dll 0x5CE8-0x5DA8: ESC &n#Wd<Name>（Regular/Thick/Bond/Thick2/Transparency/Thin/Envelopes/Envthick/Envthin/Recycled/Label/Postcard） |
| 送纸来源 | LEPRM13A.DSI [InputSlot] L49-55 | AutoSelect/Tray1/Tray2/Manual/MPTray | [InputSlot_Command] L122-127: ESC &l#H（Tray1=&l1h1001H, MPTray=&l4h1001H, Manual=&l2H） |
| 分辨率 | LEPRM13A.DSI [Resolution] L61-64 | 300/600/1200 | leenm13a.dll 0x5C10-0x5C48: &u300D+*t300R / &u600D+*t600R / &u1200D+*t1200R；PJL: @PJL SET RESOLUTION= |
| 省墨 TonerSave | DSI PrintProfilePreset TONERSAVE_TONERSAVEICON（L430）；UI 字符串 省墨模式(&M) | 预设图标 | PJL: @PJL SET ECONOMODE=（leenm13a 0x59A0） |
| 暗度 Density | DSI DriverInfo DensityAdjustment=1 (L287) | 暗度调节 | PJL: @PJL SET DENSITY=（leenm13a 0x59F0） |
| 双面 Duplex | DSI DriverInfo ManualDuplex=1(L265)/UnitDuplex=1(L266)；[Capability] PaperSize_UnitDuplex(L411)/PaperSize_ManualDuplex(L412) | 单/双面枚举 UI 名 Long Edge (Automatic)/Short Edge (Automatic)/Long Edge (Manual)/Short Edge (Manual)/Booklet | PJL: @PJL SET DXBACKSIDEFIRSTSENDMODE=（0x5AC0）；手动双面提示 @PJL SET MANUALDPX=FACE/BACK（0x5B98/0x5BB8） |
| N-up / Poster / Booklet | DSI L331-340 MultiplePage*、L327-329 BookletDivide* | 2/4/9/16/25 合页、4/9/16/25 海报、册子拆分 1-15 册 | 驱动内部拼版（无打印机命令），UI: 小册子打印方式=一册输出/拆分为多册输出 |
| 水印 Watermark | DSI L353-375（SampleWatermarkColor/WatermarkBringToFront/WatermarkOutlineText/WatermarkOverlayMethod_Default） | 背景水印/编辑模板 | 驱动内部绘制（leenm13a BrEncDrawWaterMarkTxt/BrEncDrawWaterMarkBmp） |
| 页码/页眉页脚 | UI STRING 224 页码/添加至页面顶端/页尾 | | leenm13a BrEncDrawHeaderFooterPrint |
| 打印质量 HQ | DSI 1200DpiMode=0x0002(L314) | 正常(600x600dpi)/精细(2400dpi 级别) | PJL: @PJL SET HQMMODE=（0x5B70） |
| 页面保护 | DSI PageProtection=0（无此型号） | | PJL: @PJL SET PAGEPROTECT=（0x59B8，机型无则不发） |
| 保密打印 SecurePrint | DSI SecurePrint=0（关闭，UI 字符串仍在） | 密码4位数字 | PJL: SET HOLD=STORE/HOLDTYPE=PRIVATE/HOLDKEY=（0x5750-0x5788） |
| 重印 Reprint | DSI Reprint=0 | | PJL: @PJL SET REPRINT=JOB/OFF（0x5720） |
| 用户认证 | DSI UserAuthentication=0；[UserInfoForUserAuthentication] L256-258 | UseLoginName | PJL: SET LOGINUSER=/USERNAME=/FLKID=/FLKPIN=（0x5788-0x5828） |
| 睡眠 | DSI SleepTime=1, SleepTimeMax=50, SleepTimeDefault=1 | 休眠时间 UI | PJL: SET/DEFAULT AUTOSLEEP=、TIMEOUTSLEEP=（0x5928-0x5980） |
| 介质直通提示 | DSI MediaType_BackCoverOpen(L420-421) | 信封/卡纸/标签开后盖 | UI 提示串（lelgm13a_zh-cn STRING 264/265） |
| 宏 Macro | DSI Macro=0（关） | 宏标识号 0..32767 | PCL: &f%dg%dF 定义、&f1x1038x8X 调用（leenm13a 0x5E78/0x6080） |
| 打印预览/归档 | GDI DSI PrintPreview=1/PrintArchive=1（L364-367）；XPS 版=0 | | lepvm13a.dll（MFC PrintPreview.Document）由 LEAL130/LEALB30 启动 |
| 介质名称命令 | leenm13a.dll | &n 命令 | ESC &n8WdRegular … &n9WdPostcard |
| 光栅方向 | leenm13a.dll | | ESC *r0F/*r3F + *rB 结束 |
| 调色剂硬件参数 | leenm13a.dll | | PJL SET TRANSFERLEVEL/TRANSFERLEVELUP/DEVBIASADJUST/LESSPAPERCURL/FIXINTENSITYUP |
| 维护 | leuim13a.dll | | @PJL EXECUTE NORMALPURGE=ALL/BLACK/COLOR、POWERPURGE、@PJL SET PERSONALITY=PCL（0x25D5F8-0x25D6B8, 0x271890） |

## 型号差异矩阵
| 键 | LJ2405D | LJ2455D | LJ2605D | LJ2655DN |
| --- | --- | --- | --- | --- |
| PrintRateA4/Letter | 28/30（型号 DSI 覆盖） | 系列 30/32 | 系列 30/32 | 系列 30/32 |
| PCLFont/TrueTypeMode/UsePrinterTrueTypeFonts/PrintFontsButton | 0 | 0 | 0 | **1/1/1/1（唯一带 PCL 字体）** |
| PaperSize（型号 DSI [Capability]） | 四型号完全相同（含 A3/B4/16K/Tabloid/自定义） | 同 | 同 | 同 |
| Duplex（主 DSI） | UnitDuplex=1 ManualDuplex=1 | 同 | 同 | 同 |
| TonerSave | TONERSAVE preset（系列级） | 同 | 同 | 同 |
| ExInit（LEEHLJ*.DAT） | 四型号 SHA256 全同：CB145B05EA764505052CB39A502EB8FA3E796ADB993EF33FE651C1D191B0A681（明文 [Default Setting] SaveSetting=0） | 同 | 同 | 同 |
| PIPELINECONFIG.XML（XPS） | 四型号 SHA256 全同：3CE5A99AF30F23DBBC26E4F34B1D3FD591C63FD1ECA1701B9AF9D5F0C33D93C1 | 同 | 同 | 同 |
| DriverType | 1111（GDI）/1121（XPS） | 同 | 同 | 同 |
| USBPRINT 硬件 ID | LENOVO LJ2405D6330 | LENOVO LJ2455D6220 | LENOVO LJ2605DDB31 | LENOVO LJ2655DN2C9A |

结论：功能能力在系列主 DSI 层完全共享；型号差异只有 打印速率覆盖（2405D 28ppm）与 LJ2655DN 的 PCL 字体支持（DN=网络+PCL）。

## UI 结构（leuim13a.dll + lelgm13a_zh-cn.dll）
- 标签页（DSI DevicePropertyTabInfo/BasicTab/AdvancedTab/PrintProfilesTab 控制）：Basic=1 Advanced=1 PrintProfiles=1（MaintenanceTab=0、StoragePrintTab=0、DestinationTab=0）
- UI 资源：lelgm13a_zh-cn.dll 70 个 DIALOG + 195 块 STRING 表（GBK 中文）；lelgm13a_en-cn.dll 英文；leuim13a 自身含 DEVMODE/PT 逻辑与 BRMD_OpenDialog/BRMD_OpenDuplexDialog
- 功能枚举原始名（STRING 1583-1585）：Simplex/Short Edge (Automatic)/Short Edge (Manual)/Long Edge (Automatic)/Long Edge (Manual)/Booklet/Booklet Reverse Flip、Watermark Overlay Method、ICM Rendering Intent
- 预设 PrintProfilePreset：GENERAL/NUP2IN1/PAPERSAVE/TONERSAVE/TWOSIDED_UNIT/HQ1200_MONOLOW/BOOKLET_UNIT/BLACKTEXT(GDI only)
