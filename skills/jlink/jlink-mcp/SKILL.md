---
name: jlink-mcp
description: 使用 SEGGER J-Link MCP 对实际 MCU 执行连接、固件下载、擦除或断点调试时使用；适用于不同芯片型号。
---

# J-Link MCP

通过已配置的 `jlink` MCP 操作目标板。将 MCP 的默认 `JLINK_DEVICE` 当作启动值，而不是本次板卡的型号证据；每次先根据用户信息、工程或板卡资料确定器件，必要时用 `search_devices` 查精确名称，再用 `set_device` 和 `check_setup` 核对。多探针时确认序列号。型号、接口或目标不明且无法查实时证据时，先完成只读检查，再询问缺失信息。

- 用户仅要求连接或诊断时，保持 Flash 不变。用户要求下载或擦除时，完成该范围内的操作和校验；不要因例行确认而中断已授权的工作。
- 固件地址和可擦写区域须以本次器件的内存布局及文件内容为准。不要把当前电脑上的 S32K312、SWD、Flash 地址或速度当作其他板卡的默认值。
- 对真实目标的写入只在目标、文件、地址范围一致后执行。发现 OTP、配置区、HSE/安全区、保护状态或不明确的擦除范围时，先核实其含义；不要以解锁、整片擦除或改写安全配置来试错。
- MCP 的成功摘要不是完整校验。下载后核对 J-Link 的编程结果，并在可行时读回比较；失败后依据原始日志定位原因，避免无依据的重复擦写。

下载、擦除或校验时读 [references/programming.md](references/programming.md)。运行状态、寄存器、断点或故障分析时读 [references/debugging.md](references/debugging.md)。仅处理 Intel HEX 且需要检查校验和、地址范围或独立读回比对时使用 [scripts/intel_hex.py](scripts/intel_hex.py)。

完成时报告实际器件和探针、使用的固件与地址范围、执行了哪些操作、校验证据以及仍未验证的目标行为。只有连接与目标一致、用户请求的操作完成且关键结果得到验证，才算完成。

首次安装或 MCP 未配置时，阅读 [references/setup.md](references/setup.md)，按成员本机路径配置服务。
