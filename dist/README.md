# 联想 LJ24/LJ26/M74/M76 系列打印机 WoA 驱动包（v4 Unidriver 重打包）—— README v2

## 产品说明

本包是联想 LJ24/LJ26/M74/M76 系列（27 个型号）打印驱动在 **Windows on ARM / x64 通用**环境下的 v4 Unidriver 重打包：以 `LJ2400WOA.INF` + 27 个 `<MODEL>.gpd` + 27 个 `manifest.ini` + `pipelineconfig.xml` 直接驱动系统自带打印管线（v4 打印模型不做任何渲染二进制分发，ARM64/x64 均由系统 PScript/Unidrv 管线渲染），因此**零架构绑定**。

v2 安装器以「**路线1：v4 签名路线**」为唯一主推路线（ARM64 上为默认且唯一显眼入口），签名流程全自动；IPP 兜底为第二入口；v3 兼容路线降级为高级选项中的可选附加（仅限 x64 机器，WoA 不适用）。

## 三路线对比总览

| 路线 | 适用平台 | 前提条件 | 功能完整度 | 重启 |
| --- | --- | --- | --- | --- |
| **路线1：v4 签名路线（主推）** | ARM64 / x64 通用 | `inf2cat.exe`（Windows SDK/EWDK 组件；缺时安装器一键 `winget install Microsoft.WindowsSDK`） | 完整（全部 27 型号进驱动 store，省墨等 OEM 项经 v4 管线可用） | 首次需重启一次 |
| **路线3：IPP 兜底（第二入口）** | ARM64 / x64 通用 | 仅需网络型号 + IP 可达（免驱动、免签名） | 基础打印（OEM 附加功能走设备 Web 管理） | 无 |
| **路线2：v3 兼容路线（可选附加）** | 仅 x64（WoA 不适用） | exe 同目录 `v3pkg\`（LJ2400V3.INF + 27 ASCII GPD，由 v3 生成任务产出） | 完整（v3 全功能） | 无（信任框点一次） |
| 高级选项：v1 直装链 | ARM64 / x64 | 驱动已签名或测试签名已开启 | 与 v1 相同（pnputil→printui 降级） | 无 |

## 路线1：v4 签名路线（主推，WoA 首选）

实测基线：**未签名 v4 包必被 `pnputil` 以 0xBCB 拒绝**；`Inf2Cat`（Windows SDK / EWDK 组件）是唯一官方签名入口。安装器把整条链自动化：

1. **inf2cat 探测**：启动时扫 `%WindowsSdkDir%` 与 `C:\Program Files (x86)\Windows Kits\10\bin\*\x86|x64\inf2cat.exe`。未检测到时界面给出「**安装 Windows SDK（含 Inf2Cat）**」一键按钮（实际执行 `winget install Microsoft.WindowsSDK --accept-source-agreements --accept-package-agreements`），并给出 EWDK 官方页链接：<https://learn.microsoft.com/windows-hardware/download-the-wdk>。
2. **复制驱动包**：`driver\` → `%ProgramData%\LenovoLJ2400WoA\driver`。
3. **生成目录**：`inf2cat /driver:<目录> /os:10_X64,10_ARM64`（要求 INF `[Version]` 节带 `CatalogFile.NTx64` / `CatalogFile.NTarm64` 指令，由驱动包生成任务负责）。
4. **自签**：`New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Lenovo WoA Test"`（已有同主题证书则复用）→ `Set-AuthenticodeSignature` 签 `.cat`。
5. **信任链**：证书导出后 `Import-Certificate` 进 `Cert:\LocalMachine\TrustedPublisher` 与 `Cert:\CurrentUser\TrustedPublisher`。
6. **测试签名**：`bcdedit /set testsigning on`（若此前已开启则跳过并**免重启直接续装**）。
7. **重启续装**：首次开启测试签名时提示「需重启一次（桌面短暂显示测试模式水印属正常）」并写入 `state.json=pending_reboot`（含型号/队列/连接方式）。重启后再跑安装器，状态机自动执行：`pnputil /add-driver LJ2400WOA.INF /install` → **EnumPrinterDrivers 验证 27 型号全部进 store** → `Add-Printer -DriverName` 建队列（失败降级 printui）→ winspool 验证 DriverName → `state.json=installed` → 管理工具与快捷方式。

## 路线3：IPP 兜底（WoA 上立即可用）

- 适用：路线1 的 SDK 尚未装好、或只需要尽快打基础打印时。
- 网络型号（后缀匹配 DN/DW/DNA/DXF/W，另收录同族 DNF/DHF/DWA）：LJ2655DN、LJ2680DN、M7490DNF、M7400W、M7405DW、M7455DNF、M7615DNA、M7625DWA、M7626DNA、M7628DNA、M7655DHF、M7675DXF、M7685DXF、M7686DXF、M7690DNA。
- 操作：填 IP → 点「**通过 IPP 自动添加打印机**」（实际执行 `Add-Printer -Name <队列> -IppUrl http://<ip>/ipp/print`）；或点「**打开系统打印设置手动添加**」（`ms-settings:printers`）。
- **IPP 模式限制**：省墨、保密箱等 OEM 附加功能不经过驱动 GPD，需在设备 Web 管理（`http://<ip>/`）中设置；打印质量/纸张由系统打印偏好接管。

## 路线2：v3 兼容路线（可选附加，仅限 x64 机器，WoA 不适用）

> 本节为可选附加：v3 渲染二进制按架构绑定，ARM64/WoA 上不可用（界面在 ARM64 机器上直接隐藏该入口）。仅 x64 机器在无法安装 SDK 时选用。

- 前提：exe 同目录 `v3pkg\LJ2400V3.INF` + 27 个 ASCII GPD（由 v3 生成任务产出；缺失时界面提示路径）。
- 操作：展开「高级选项」→ 选路线2 → 开始安装 → **执行时会弹 Windows 信任提示，请点『仍要安装此驱动程序软件』**。
- 实测：信任框无人点击时进程以 **0x4C7（ERROR_CANCELLED）** 结束——安装器识别该码并提示重试。
- 成功后同样走 winspool 队列验证 + 管理工具安装，`state.json=installed`。

## 高级选项：v1 直装链（保留）

勾选「v1 直装链」后「开始安装」走 v1 流程（忽略上方所选路线）：复制驱动包 → `pnputil /add-driver /install` → 降级链 `printui /if /b /f /r /m` 建队列 → winspool 验证 → 管理工具与快捷方式。适合驱动已签名或测试签名已开启的环境；未签名 v4 包在 pnputil 步骤实测被 0xBCB 拒，安装器记录后自动降级 printui（信任框点一次）。

## 状态机（state.json）

位置：`%ProgramData%\LenovoLJ2400WoA\state.json`。字段：state / route / model / queue / connection / ip / note / timestamp。

```
（全新）→ pending_signature（路线1 签名链进行中/失败保留重试）
        → pending_reboot（签名完成 + testsigning on，等重启）
        →（重启后自动续装）→ ready（pnputil 进 store，27 型号验证通过）
        → installed（队列验证通过）
```

损坏/缺失一律按全新安装处理（自检 `/selftest-state` 覆盖四状态往返与容错）。

## 安装通用步骤

1. 把 `driver\` 子目录放到 `LJ2400Setup.exe` 同目录；双击 `LJ2400Setup.exe`（UAC 点「是」，清单 requireAdministrator）。
2. 选连接方式（USB 自动识别 `HKLM\...\Enum\USBPRINT`；网络填 IP 由 `Add-PrinterPort` 建 RAW 9100 端口；仅安装驱动只跑预装不建队列）。
3. 点「开始安装」，日志实时显示并写入 `%ProgramData%\LenovoLJ2400WoA\setup.log`。
4. 完成后点「打开打印机管理」（开始菜单/桌面快捷方式「联想打印机管理」同步创建）。

## 打印机管理工具（LJ2400Manager.exe）用法

- 顶部「本机队列」下拉列出本机队列（winspool 枚举），选中后自动解析端口对应的打印机 IP（TCP/IP 端口从注册表 `Standard TCP/IP Port\Ports\<端口名>` 读取；`IP_x.x.x.x` 命名端口也可从端口名直解）。`USB`/`WSD`/`PORTPROMPT`/`FILE:` 端口没有网络地址，需手动填 IP。
- **查询状态**：全量查询 ——
  - 型号 `1.3.6.1.2.1.25.3.2.1.3.1`（hrDeviceDescr）
  - 设备状态 `1.3.6.1.2.1.25.3.2.1.7.1` + 打印机状态 `1.3.6.1.2.1.25.3.5.1.1.1`
  - winspool 队列状态位（离线/卡纸/缺纸/墨粉不足/盖板打开等中文映射）
  - 总页数 `1.3.6.1.2.1.43.10.2.1.4.1.1`
  - **Brother 私有分支**：`1.3.6.1.4.1.2435.*` 全部 41 个 OID（含 `.63/.67/.99/.64/.68` 分支，表来自 `lerbm13a.dll` 字符串区提取）逐个 GET，凡有响应显示「OID = 原始值」+ 智能猜测（原始值 0-100 显示 `≈N%`，**标注阈值待真机校准**）；按 墨粉/纸盒/保密箱 分组。
  - PJL 通道：`@PJL INFO STATUS` 与 `@PJL DINQUIRE SERIALNUMPRN`（TCP 9100，原始响应在底部文本框）。
- **刷新状态(本地)**：只刷队列列表与 winspool 状态位，不联网。
- **打印测试页**：`rundll32 printui.dll,PrintUIEntry /k /n "<队列>"`。
- **打开设备 Web 管理**：浏览器打开 `http://<ip>/`。
- **导出状态报告(JSON)**：把当前查询结果导出为 JSON（手写序列化，无第三方依赖）。
- 所有网络任务异步执行（Task.Run + CancellationToken，单次 3 秒超时）；设备离线显示「无法连接（检查 IP/联机）」。

## 真机采样校准流程（snmp_sample.py）

1. 电脑与打印机同一网段，确认 `ping <打印机IP>` 通。
2. 运行采样（Python 3.13，无第三方库）：

   ```
   python tools\snmp_sample.py --ip 192.168.1.100 --out result.json
   ```

3. 把 `result.json` 发回开发侧，用于：①确认 41 个私有 OID 的语义；②把 Manager 里 `≈N%` 的猜测阈值换成真机刻度。

## 600dpi 栅格运行期验证口径

- **当前已验证**：27 个 GPD 语法级检查通过；`pipelineconfig.xml` 与 manifest 静态核对 32/32 全通过。
- **真机打印是唯一真实验证**：安装完成（路线1/路线2/高级选项任一）后打印测试页，核对输出分辨率确为 600dpi、无斜线锯齿与错位。IPP 路线的输出由系统管线与设备固件协商，不适用本口径。

## 已知限制

- **墨粉百分比阈值待校准**：私有 OID 的 0-100 数值到百分比映射是猜测值，等真机采样后校准。
- **未签名包**：无 WHQL 签名——路线1 通过自签+TrustedPublisher+testsigning 解决；路线2/高级选项在建队列时信任框弹一次。
- **测试签名水印**：路线1 首次开启 testsigning 后桌面右下角显示「测试模式」水印，属系统正常提示，重启后持续存在直到 `bcdedit /set testsigning off`。
- **USB PnP ID 仅 4 型号已收录**：USB 自动识别按设备描述匹配 27 个型号全部可用，但 USBPRINT PnP 硬件 ID 别名表只完整覆盖 4 个主力型号，其余型号走安装器下拉选型（INF 解析兜底也已内置）。
- 私有 OID 未响应属正常：不同型号固件支持的分支不同，无响应行不显示。
- IPP 路线无 OEM 附加功能（见路线3 限制）。

## 构建方法

```
powershell -ExecutionPolicy Bypass -File tools\build.ps1
```

- 唯一编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（C#5 语法）；
- `/target:winexe /platform:anycpu`，Setup 挂 `app.manifest`（requireAdministrator）；
- 产物落 `dist\`：`LJ2400Setup.exe`、`LJ2400Manager.exe`、`build_log.txt`；
- 自检入口：`LJ2400Setup.exe /selftest-state`（结果 `selftest_state.txt`）与 `/selftest-arch`（结果 `selftest_arch.txt`），退出码 0=全 PASS；
- `driver\` 产物存在时一并打 `dist\LJ2400-WoA-bundle.zip`（driver\ + 两个 exe + README.md）；不存在则跳过打包并提示「待生成器产出」。
- 零第三方依赖：无 NuGet、无外部 DLL；SNMP 客户端为手写 ASN.1/BER，PJL 为原生 TcpClient。
