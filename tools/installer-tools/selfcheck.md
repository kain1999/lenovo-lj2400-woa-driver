# LJ2400WoA 安装器/管理工具 自检报告 v2（自检①②③④⑤）

生成时间：2026-11-16（v2 轮）　执行者：static 角色（工程编码子会话）

## 自检① csc 编译零错误 —— PASS

- 编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（唯一编译链，C#5 语法）
- 命令：`csc /nologo /target:winexe /platform:anycpu /optimize+ /win32manifest:app.manifest /out:dist\LJ2400Setup.exe Setup\Program.cs` → **exit 0，0 error 0 warning**（一次通过）
- Manager 未改动，沿用 v1 产物（37,888 B，SHA256 0D4562392AD6F2EA...，与 v1 一致）
- `LJ2400Setup.exe` v2：**69,632 B**，SHA256 **590337AEFE2D583AB16E9E753545EBBABB5DCC4C28F0870577C21AF38203C3A6**

## 自检② PE 为 MSIL AnyCPU —— PASS（tools\pe_check.py）

| 产物 | Machine | Magic | CLR Flags | 判定 |
| --- | --- | --- | --- | --- |
| LJ2400Setup.exe (v2) | 0x014C (I386) | 0x010B (PE32) | 0x00000001 ILONLY=1，32BITREQUIRED=0，32BITPREFERRED=0 | MSIL AnyCPU |
| LJ2400Manager.exe | 0x014C (I386) | 0x010B (PE32) | 0x00000001 ILONLY=1，32BITREQUIRED=0，32BITPREFERRED=0 | MSIL AnyCPU |

ARM64（WoA）与 x64 均按本机 64 位 JIT，无 32BITPREFERRED（不走 x86 模拟）。

## 自检③ 三路线代码路径走查 —— PASS（v2 新增）

主次裁决（按用户纠偏实现）：

| 路线 | UI 位置 | ARM64 (WoA) | x64 | 代码路径 |
| --- | --- | --- | --- | --- |
| 路线1 v4 签名 | 主界面默认单选（唯一主推） | ✅ 默认且唯一显眼 | ✅ 主推 | `RunRouteV4Signed` → `SigningWorkflow.Run` →（testsigning 已开启则免重启）`ContinuePendingReboot` |
| 路线3 IPP | 主界面第二单选 | ✅ 可用 | ✅ 可用 | `RunIppAdd`（`Add-Printer -IppUrl http://<ip>/ipp/print`） |
| 路线2 v3 | 高级选项折叠面板内单选 | ❌ 面板整体隐藏（`ApplyArchitectureUi`） | ✅ 展开可用（标注"仅限 x64 机器的可选附加，WoA 不适用"） | `RunRouteV3`（printui /if，0x4C7=1223 识别为取消→提示重试） |
| v1 直装链 | 高级选项面板内勾选 | ✅ | ✅ | `DoInstall`（pnputil→printui 降级链，v1 原样保留） |

关键分支逐一核对：

1. **路线1 全链**：inf2cat 探测（`Inf2CatLocator.Find`：`%WindowsSdkDir%` + 两个 Windows Kits 根，版本目录降序，x86/x64/根三级找）→ 缺失时 `btnInstallSdk`（`winget install Microsoft.WindowsSDK --accept-source-agreements --accept-package-agreements`，超时 30 min，装完重探测）→ 复制驱动包 → `state.json=pending_signature` → inf2cat `/os:10_X64,10_ARM64`（失败提示 CatalogFile.NTx64/NTarm64 指令缺失）→ 自签脚本（EncodedCommand：先查 `CN=Lenovo WoA Test` 证书复用，无则 `New-SelfSignedCertificate -Type CodeSigningCert`，`Set-AuthenticodeSignature` 校验 `Status -eq 'Valid'`，`Export-Certificate` + 双 `Import-Certificate` 进 LocalMachine/CurrentUser\TrustedPublisher）→ `bcdedit /set testsigning on`（预查 `/enum {current}`，已开启则跳过并免重启直接续装）→ `pending_reboot` + 提示重启。
2. **重启续装链**：`OnLoad` → `HandlePendingState` 读 state.json → `pending_reboot` 用户确认 → `ContinuePendingReboot`：testsigning 确认 → `pnputil /add-driver LJ2400WOA.INF /install`（`PnputilLooksOk`：exit 0 且无 `0x8???????` HRESULT/拒绝/失败/无法/error/failed；被拒回写 `pending_signature` 附 0xBCB 提示）→ `EnumPrinterDrivers`(winspool level 2) **27 型号 store 验证**（`CountInstalledModels` 对常量表逐项匹配）→ `state.json=ready` → 建队列（仅驱动模式跳过；`Add-Printer -Name -DriverName -PortName` 优先，失败降级 printui /if）→ `GetPrinterInfo2` 验证 DriverName==型号 → 管理工具+快捷方式 → `installed`。
3. **路线2 分支**：ARM64 直接拦截（界面隐藏 + 代码双保险）→ v3pkg 缺失提示路径 → 确认框明示信任框操作 → printui 退出码 1223(0x4C7) 识别为「信任框被取消/无人点击」→ 提示重试；0 → 队列验证 → installed。
4. **路线3 分支**：IP/队列校验 → `Add-Printer -IppUrl`（EncodedCommand）→ 队列存在性验证 → OEM 功能提示走设备 Web 管理（`ms-settings:printers` 手动添加入口也在）。
5. **状态机写点**：pending_signature（路线1 开始/签名失败/pnputil 被拒）→ pending_reboot（签名完成待重启）→ ready（store 27 型号验证通过）→ installed（队列验证通过）；IPP 不写状态（免驱动路线不进状态机）。

## 自检④ 按钮 Handler 逐个走查 —— PASS（无 TODO / 无占位 / 无第三方依赖）

机器证据：`Select-String "TODO|FIXME|占位|待补|省略|自行补全"` → **0 命中**；全部 `using` 均为 BCL（System.* / System.Windows.Forms / Microsoft.Win32）。

| Handler | 行为 | 异常路径 |
| --- | --- | --- |
| `_btnInstall_Click` | 按路线分派：v1 直装链勾选优先（-1）；否则 签名(0)/v3(1)/IPP(2)；逐路线参数校验 | try/catch 全包 + 每分支 MessageBox 可操作提示 |
| `_btnInstallSdk_Click` | winget 装 Windows SDK（30 min 超时）→ 重探测 inf2cat → 刷新推荐与提示 | 无 winget → 引导 EWDK 链接文本 |
| `_btnIppAdd_Click` / `_btnIppSettings_Click` | IPP 自动添加 / `ms-settings:printers` | 失败提示 ping/手动添加 |
| `_btnOpenManager_Click` | 启动 `%ProgramData%\LenovoLJ2400WoA\LJ2400Manager.exe` | 缺文件提示重装 |
| 路线单选/折叠开关 | `UpdateRouteUi` 动态提示 + 按钮显隐；ARM64 隐藏高级面板 | — |

## 自检⑤ 内置单测（winexe 自检入口，退出码断言）—— PASS

- `LJ2400Setup.exe /selftest-state` → **exit 0**，`dist\selftest_state.txt`：
  - [PASS] 缺失 state.json 时 Read() 返回 null
  - [PASS] pending_signature / pending_reboot / ready / installed 四状态写入/读回八字段一致
  - [PASS] 损坏 state.json 容错返回 null（并清场不留脏状态）
- `LJ2400Setup.exe /selftest-arch` → **exit 0**，`dist\selftest_arch.txt`：
  - `GetNativeSystemInfo().wProcessorArchitecture = 9 → x64`（本机），返回值 ∈ {0,9,12} 集合 PASS
  - 与 `PROCESSOR_ARCHITECTURE=AMD64` 环境变量交叉验证 PASS；`IsArm64()` 判定一致性 PASS
  - ARM64 判定值 12 的语义在 `ArchDetect.PROCESSOR_ARCHITECTURE_ARM64` 常量与 UI/推荐逻辑中同源使用

## 自检⑥ 型号表对账 —— PASS（tools\model_reconcile.py）

- C# 常量表 27 项 / ppd_extract.json 27 项：**顺序与内容完全一致（27/27）**，exit 0（v2 未改动常量表）。

## 结论

v2 六项自检全部 PASS。三路线主次与纠偏要求一致：WoA 主线（签名路线唯一主推 + IPP 第二入口）在前，v3 在高级折叠区且 ARM64 整体隐藏；签名链、状态机、续装链均有代码级落点；驱动包目录仍空（生成器任务产出后 bundle 自动恢复）。
