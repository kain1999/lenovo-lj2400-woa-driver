# LJ2400WoA 安装器/管理工具 自检报告（双路线版）

生成时间：2026-11-16（本轮）　执行者：static 角色（工程编码子会话）

## 自检① csc 编译零错误 —— PASS

- 编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（唯一编译链，C#5 语法）
- 命令：`csc /nologo /target:winexe /platform:anycpu /optimize+ /r:System.Net.Http.dll /win32manifest:app.manifest /out:dist\LJ2400Setup.exe Setup\Program.cs` → **exit 0，0 error 0 warning**（一次通过）
- Manager 未改动沿用既有产物；构建脚本 `tools\build.ps1` 已加 `/r:System.Net.Http.dll` 并以 UTF-8 BOM 重存（powershell.exe 5.1 可正确解析中文注释）
- 产物（最终构建）：
  - `LJ2400Setup.exe`：**68,608 B**，SHA256 **C47EF277E717899ECC2BA9A95FE9A475F33DCE7D8CA1F976802472B43458EAAE**
  - `LJ2400Manager.exe`：**37,888 B**，SHA256 **C86BDA060A7E4E31DBE5838483573743A03A268640DDDEAAA860F72B9FC74708**
  - `LJ2400-WoA-bundle.zip`：**206,882 B**，SHA256 **B047C3808A09165B8C7569E30D0AD1E06CF4A52B21A00CA7742C9B886E0301B4**

## 自检② PE 为 MSIL AnyCPU —— PASS（tools\pe_check.py）

| 产物 | Machine | Magic | CLR Flags | 判定 |
| --- | --- | --- | --- | --- |
| LJ2400Setup.exe | 0x014C (I386) | 0x010B (PE32) | 0x00000001 ILONLY=1，32BITREQUIRED=0，32BITPREFERRED=0 | MSIL AnyCPU |
| LJ2400Manager.exe | 0x014C (I386) | 0x010B (PE32) | 0x00000001 ILONLY=1，32BITREQUIRED=0，32BITPREFERRED=0 | MSIL AnyCPU |

ARM64（WoA）与 x64 均按本机 64 位 JIT，无 32BITPREFERRED（不走 x86 模拟）。

## 自检③ 两路线代码路径走查 —— PASS（本轮改版后重查）

主次裁决（用户纠偏：仅两条路线）：

| 路线 | UI 位置 | ARM64 (WoA) | x64 | 代码路径 |
| --- | --- | --- | --- | --- |
| 签名安装路线（推荐） | 主界面默认单选（唯一主推） | ✅ 默认 | ✅ 主推 | `RunRouteSigned` → `SigningWorkflow.Run` →（testsigning 已开启则免重启）`ContinuePendingReboot` |
| IPP 路线（基础打印） | 主界面第二单选 | ✅ 可用 | ✅ 可用 | `RunIppAdd`（`Add-Printer -IppUrl http://<ip>/ipp/print`） |

关键分支逐一核对：

1. **签名安装路线全链**：inf2cat 探测（`Inf2CatLocator.Find`：`%WindowsSdkDir%` + 两个 Windows Kits 根，版本目录降序，ARM64\→x86\→x64\→根四级找）→ 缺失时 `btnInstallSdk`：**HttpClient 下载微软官方安装器直链**（`https://go.microsoft.com/fwlink/?linkid=2382519` → `%TEMP%\winsdksetup.exe`，ProgressBar 进度）→ `winsdksetup.exe /features OptionId.SigningTools /q /norestart` 静默安装（30 min 超时，退出码与输出原样落日志）→ 装完重探测 inf2cat → 复制驱动包 → `state.json=pending_signature` → inf2cat `/os:10_X64,10_ARM64`（失败提示 CatalogFile.NTx64/NTarm64 指令缺失）→ 自签脚本（EncodedCommand：先查 `CN=Lenovo WoA Test` 证书复用，无则 `New-SelfSignedCertificate -Type CodeSigningCert`，`Set-AuthenticodeSignature` 校验 `Status -eq 'Valid'`，`Export-Certificate` + 双 `Import-Certificate` 进 LocalMachine/CurrentUser\TrustedPublisher）→ `bcdedit /set testsigning on`（预查 `/enum {current}`，已开启则跳过并免重启直接续装）→ `pending_reboot` + 提示重启。
2. **SDK 异常分支**：静默退出码非 0 **或** 探测仍失败 → `OpenSdkGui` 直接运行 `winsdksetup.exe`（GUI 模式）+ 提示用户在安装器中勾选组件完成安装 → 装完点「**重新检测 Inf2Cat**」（`_btnRedetect_Click` 重探测 + 刷新推荐）；下载失败 → 自动打开官方下载页 `https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads`。
3. **重启续装链**：`OnLoad` → `HandlePendingState` 读 state.json → `pending_reboot` 用户确认 → `ContinuePendingReboot`：testsigning 确认 → `pnputil /add-driver LJ2400WOA.INF /install`（`PnputilLooksOk`：exit 0 且无 `0x8???????` HRESULT/拒绝/失败/无法/error/failed；被拒回写 `pending_signature` 附 0xBCB 提示）→ `EnumPrinterDrivers`(winspool level 2) **27 型号 store 验证**（`CountInstalledModels` 对常量表逐项匹配）→ `state.json=ready` → 建队列（仅驱动模式跳过；`Add-Printer -Name -DriverName -PortName` 优先，失败降级 printui /if）→ `GetPrinterInfo2` 验证 DriverName==型号 → 管理工具+快捷方式 → `installed`。
4. **IPP 分支**：IP/队列校验 → `Add-Printer -IppUrl`（EncodedCommand）→ 队列存在性验证 → OEM 功能提示走设备 Web 管理（`ms-settings:printers` 手动添加入口也在）。
5. **状态机写点**：pending_signature（签名开始/签名失败/pnputil 被拒）→ pending_reboot（签名完成待重启）→ ready（store 27 型号验证通过）→ installed（队列验证通过）；IPP 不写状态（免驱动路线不进状态机）。
6. **输出解码**：`Proc.OutputEncoding = UTF-8`，`StandardOutputEncoding/StandardErrorEncoding` 统一挂 UTF-8（修复 cmd/powershell 中文输出乱码）。

## 自检④ 按钮 Handler 逐个走查 —— PASS（无 TODO / 无占位 / 无第三方依赖）

机器证据：`Select-String "TODO|FIXME|占位|待补|省略|自行补全"` → **0 命中**；全部 `using` 均为 BCL（System.* / System.Net.Http / System.Windows.Forms / Microsoft.Win32）。

| Handler | 行为 | 异常路径 |
| --- | --- | --- |
| `_btnInstall_Click` | 按路线分派：签名安装路线(0)/IPP 路线(1)；逐路线参数校验 | try/catch 全包 + 每分支 MessageBox 可操作提示 |
| `_btnInstallSdk_Click` | HttpClient 下载官方安装器（进度条）→ SigningTools 静默安装 → 重探测 inf2cat → 刷新推荐与提示 | 静默非 0/探测失败 → 自动转 GUI 安装器；下载失败 → 自动开官方下载页 |
| `_btnRedetect_Click` | GUI 安装完成后重探测 inf2cat | 未命中提示确认勾选 SigningTools 组件 |
| `_btnSdkPage_Click` | 打开官方下载页（次入口） | 打开失败弹 URL 手动访问 |
| `_btnIppAdd_Click` / `_btnIppSettings_Click` | IPP 自动添加 / `ms-settings:printers` | 失败提示 ping/手动添加 |
| `_btnOpenManager_Click` | 启动 `%ProgramData%\LenovoLJ2400WoA\LJ2400Manager.exe` | 缺文件提示重装 |
| 路线单选 | `UpdateRouteUi` 动态提示 + 按钮显隐 | — |

## 自检⑤ 内置单测（winexe 自检入口，退出码断言）—— PASS（最终构建复跑）

- `LJ2400Setup.exe /selftest-state` → **exit 0**，`dist\selftest_state.txt`：
  - [PASS] 缺失 state.json 时 Read() 返回 null
  - [PASS] pending_signature / pending_reboot / ready / installed 四状态写入/读回八字段一致
  - [PASS] 损坏 state.json 容错返回 null（并清场不留脏状态）
- `LJ2400Setup.exe /selftest-arch` → **exit 0**，`dist\selftest_arch.txt`：
  - `GetNativeSystemInfo().wProcessorArchitecture = 9 → x64`（本机），返回值 ∈ {0,9,12} 集合 PASS
  - 与 `PROCESSOR_ARCHITECTURE=AMD64` 环境变量交叉验证 PASS；`IsArm64()` 判定一致性 PASS
- `LJ2400Setup.exe /selftest-sdk` → **exit 0**，`dist\selftest_sdk.txt`（本轮新增）：
  - 打印：下载直链（`https://go.microsoft.com/fwlink/?linkid=2382519`，标注官方安装器 x86 二进制 WoA 模拟层可运行）、本地安装器路径 `%TEMP%\winsdksetup.exe`、静默命令（`/features OptionId.SigningTools /q /norestart`）、异常路径（静默非 0/探测失败 → GUI 安装器 → 「重新检测 Inf2Cat」）、官方下载页、输出解码 utf-8、inf2cat 探测根与子目录顺序（ARM64\→x86\→x64\→版本根）
  - [PASS] 直链常量正确 / 静默参数含 SigningTools+/q+/norestart / 官方页 URL / 输出统一 UTF-8 / 探测根 ≥2 / 子目录顺序含 ARM64、x86、x64
  - **不实际下载**（纯常量与探测路径断言，exit 0）

## 自检⑥ 型号表对账 —— PASS（tools\model_reconcile.py）

- C# 常量表 27 项 / ppd_extract.json 27 项：**顺序与内容完全一致（27/27）**，exit 0（本轮未改动常量表）。

## 禁词清查 —— PASS

- `兜底`：README.md / Manager.cs / Program.cs / build.ps1 → **0 命中**
- `v1|v2|v3|V1|V2|V3`：README.md / Manager.cs / Program.cs / build.ps1 → **0 命中**（app.manifest 的 asm URN 命名空间与 snmp_sample.py 的协议版本号属格式必需，不在叙述性标签清查范围）
- `winget`：Program.cs → **0 命中**（SDK 引导整体切换官方安装器直链）

## 结论

本轮七项自检全部 PASS。双路线结构与纠偏要求一致：签名安装路线唯一主推 + IPP 路线第二入口，ARM64 与 x64 界面一致；SDK 引导已按真机实测修正（winget → 官方安装器直链下载 + SigningTools 静默 + GUI 转换 + 重新检测），子进程输出统一 UTF-8；签名链、状态机、续装链均有代码级落点；驱动包目录仍空（生成器任务产出后 bundle 自动恢复）。
