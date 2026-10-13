# 本地资料与证据

## 随附资料位置

- 资产目录：相对于技能根目录的 `assets/data/`。从本文件进入 [数据资产清单](../assets/data/数据资产清单.md)、[RM 章节索引](../assets/data/S32K3XXRM_章节索引.md)、[Data Sheet 章节索引](../assets/data/S32K3xx_章节索引.md)。
- 下文未带目录的 PDF/XLSX 文件名均指该目录内文件。脚本示例从技能根目录运行；从其他工作目录调用时，先根据当前 `SKILL.md` 所在目录解析脚本与资产的绝对路径，不使用固定用户名路径。
- 资料覆盖整个 S32K3xx 系列，不扩大本技能的 S32K310/311/312/314 支持范围；其他型号附件仅作明确标注的参考。

## 外部工具位置与已观察事实

以下是 2026-09-26 的只读盘点，不是成员机器的安装默认值，也不是对后续机器状态或最新版本的保证。S32DS/RTD 不随技能打包；重新使用时按成员实际路径运行安装盘点。
- IDE 根目录：`C:\NXP\S32DS.3.6.6`，启动器在 `eclipse\s32ds.exe`、控制台启动器 `eclipse\s32dsc.exe`。
- SDK：`S32DS\software\PlatformSDK_S32K3`，驱动位于 `RTD\<Module>_TS_*`。
- `sdk_manifest.xml` 根属性 `name` 为 `S32K3_S32M27x AUTOSAR R21-11 RTD 5.0.0 D2410`，根 `api_version=5.0.0`，内部 `ksdk` 的 `version=4.0.0`。这些字段不能混为一个版本；选择工程版本时结合 IDE 软件包信息、头文件/发布文档确认。
- 初次盘点未找到 S32K31X 的官方 `.mex` 示例；需要示例时重新检查当前安装，不把其他型号示例当作可直接使用的基线。
- Config Tools 文档包：`eclipse\plugins\com.nxp.swtools.doc.uct_1.9.4.202607201458.jar`。这是文档插件版本，不能当成全部工具模块版本；Pins/Clocks/Peripherals 的版本也可能彼此不同。

## 资料选择

| 需求 | 优先入口 | 必须继续核对 |
| --- | --- | --- |
| 型号能力、封装、时钟/电气边界 | `S32K3xx.pdf`；章节索引中的 Feature comparison、Ordering、Clocking、I/O | 正确型号列、脚注、供电和温度条件 |
| 模块工作原理、寄存器、chip-specific 限制 | `S32K3XXRM.pdf` 与章节索引 | 通用模块描述与芯片专属小节同时读取 |
| 硅片勘误与 workaround | 下方对应型号及 mask set 的勘误 PDF | 先确认实际 mask；按勘误条目的触发条件核对本次外设/模式 |
| 引脚和输入选择 | 对应 IOMUX 工作簿 | 型号适用性、封装列、IO Signal Table、Input Muxing、Supplies、备注 |
| DMA、IRQ、触发路由 | `S32K3xx_DMAMUX_map.xlsx`、`S32K3xx_interrupt_map.xlsx`、`S32K3xx_TRGMUX_connectivity.xlsx` | 型号/实例列；不要只凭命中某个信号名称 |
| 地址、访问保护、故障 | memory_map、REG_PROT、fault_map 附件 | 型号、权限、主设备和模式 |
| RTD API/字段、初始化例子 | 对应 `RTD\<Module>_TS_*\doc`、`include`、`config`、`examples\S32DS` | 驱动层级与版本；示例芯片不能代替目标芯片 |
| IDE 创建/生成/CLI | 下述本机 JAR 内帮助 | 按安装版本定位，禁止猜 CLI 参数 |

资产清单记录：RM Rev.12（2025-11-11），Data Sheet Rev.14（2026-04-10）。引用时回读封面/目标页确认；章节索引的 `pN` 是 **1-based PDF 页序**，不是印刷页码。XLSX 修订信息先读 `Title`，资料查询用本技能 `asset_query.py`。

## 本地 mask set 勘误

以下三份 PDF 的产品、mask、修订版和日期来自各自封面第 1 页；它们是 **mask 专属资料**，不能仅凭型号相同就断言适用，也不表示已经核对 NXP 最新版本。

| 目标 MCU | 适用 mask | 文件 | 本地版本 |
| --- | --- | --- | --- |
| S32K310 / S32K311 | `0P98C` | `S32K311_0P98C.pdf` | Rev. 6，2025-07-24 |
| S32K312 | `0P09C` | `S32K312-0P09C-ERRATA.pdf` | Rev. 9，2025-07-24 |
| S32K314 | `0P55A` / `1P55A` | `S32K3X4-0P55A-1P55A-ERRATA.pdf` | Rev. 4，2025-07-24；封面还列 S32K324、S32K344 |

先从芯片标识/硬件记录确认实际 mask，并结合文档第 1 页的产品范围与 JTAG ID 交叉核对；未知时标注“勘误适用性未确认”，不能把这三份当作所有 S32K31X 的通用勘误。`0P55A` 与 `1P55A` 在该文档第 1 页给出同一 JTAG ID，不能仅凭该 ID 区分两者。确认适用后，按本次外设和模式定位具体 erratum ID、触发条件、影响及 workaround，再与 RM/数据手册和当前 RTD 实现核对；引用给出文件、修订版、erratum ID 与 PDF 页序。

## IOMUX 共用工作簿

| 目标 MCU | 工作簿 | 已观察的信号/输入 Sheet 前缀 |
| --- | --- | --- |
| S32K310 / S32K311 | `S32K311_S32K310_IOMUX.xlsx` | `S32K311_IO Signal Table`、`S32K311_Input Muxing` |
| S32K312 | `S32K312_IOMUX.xlsx` | `S32K312_IO Signal Table`、`S32K312_Input Muxing` |
| S32K314 | `S32K344_S32K324_S32K314_IOMUX.xlsx` | `S32K344_IO Signal Table`、`S32K344_Input Muxing` |

共用主 Sheet 只定位候选；特别是 S32K314 工作簿以 S32K344 为主 Sheet，不能把其资源或封装列直接用于 S32K314。以完整订货号、Data Sheet、型号/封装 Sheet 和当前工具选择项核实；与 SDK manifest 不一致时不能任选一方。

`asset_query.py xlsx` 只回填真实合并单元格并标注 `source_cell`，不自动填充分组留白。功能行缺 Port/MSCR/封装数据时，沿所属 pad 组核对显式起始行、边界、表头和备注；输出仍是候选原始数据，不是芯片适用性判决。

## 本机帮助定位

JAR 是 ZIP，可只读指定成员，无需解压整个安装包。可通过 `asset_query.py help` 按文件名查询，再以 `--entry` 读取正文。

`com.nxp.s32ds.doc.platform.reference_*.jar`：

- `com.nxp.s32ds.doc.s32ds/reference/new_s32ds_application_project_wizard.html`
- `com.nxp.s32ds.doc.s32ds/reference/project_name_and_type_app.html`
- `com.nxp.s32ds.doc.common/tasks/creating_s32ds_project_from_example.html`
- `com.nxp.s32ds.doc.s32ds/tasks/editing_device_configuration.html`
- `com.nxp.s32ds.doc.s32ds/tasks/using_sdk_in_projects.html`

`com.nxp.swtools.doc.uct_*.jar` 中 `resources-ide/support/help/en/topics/`：

- `command_line_execution.html`
- `command_line_execution_-_working_with_projects.html`
- `command_line_execution_-_pins_tool.html`
- `command_line_execution_-_clocks_tool.html`
- `command_line_execution_-_peripherals_tool.html`

优先 `resources-ide` 的集成版文档，避免误用独立工具版。官方文档某些例子仍用 `eclipsec.exe`，本机实际存在的是 `s32dsc.exe`；运行前检查实际文件并通过日志验证，不能把文档例子当成本机已运行记录。
