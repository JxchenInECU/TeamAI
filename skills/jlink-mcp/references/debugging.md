# 运行调试与故障定位

先核实本次目标器件、探针和接口，参照 `programming.md` 的“确定本次目标”。调试请求本身不授权改写 Flash、配置寄存器或安全状态。

- 从 `device_info`、`snapshot`、`read_registers`、`read_memory` 与用户描述的症状取得当前证据。需要稳定寄存器/栈快照时用 `halt`；记录操作前是否在运行，并在诊断完成后按用户意图 `resume`。连接、复位及部分读取可能改变目标运行状态，因此记录执行过的动作。
- 故障异常用 `diagnose_crash` 读取并解码 Cortex-M fault 寄存器，再结合 PC、LR、栈和反汇编或 ELF 符号核对原因。不要从一条异常位直接断言根因。
- 需要源码级调用栈时提供**与目标镜像同构建**的 ELF，使用 `gdb_load` 的默认符号加载方式（`flash=false`）；只有用户要求重新下载时才设 `flash=true`。需要命名外设字段时使用与本次芯片匹配的 SVD 和 `set_svd_path`。缺少这些文件时仍可做原始地址级诊断，并说明解释范围。
- 用 `gdb_server_start`/`gdb_connect`、断点、单步和 `gdb_wait` 时注意 J-Link 同时只服务一个调试客户端。结束由本次任务启动的 GDB 会话与服务器，避免占住探针。`probe_command` 或 Flash 操作前处理已有会话冲突。
- 若 `read_memory` 未包含请求的首地址、输出混有连接日志，改用 `probe_command` 的 `mem`/`mem32` 或 `savebin` 复核；不要把工具返回了文本当作读到了所需数据。

## 断点、单步与观察点

核对当前运行镜像和目标核；地址断点必须属于这次运行的代码。需要按函数或源码行定位时，先用同一构建的 ELF 加载符号（`gdb_load` 默认 `flash=false`），再经 `gdb_command` 设置 `break 函数名` 或 `break 文件:行号`。已知地址可用 `set_breakpoint({"address":"0x..."})`。用 `gdb_command({"command":"info breakpoints"})` 检查 GDB 给出的编号、启用状态与实际落点；不要只凭“设置成功”判定位置正确。硬件断点和观察点数量随芯片及探针而异。

让目标 `resume`/`continue` 后，检查停止原因；命令超时而目标仍在运行时用 `gdb_wait` 等待。只有停因和 PC/命中地址相符才报告断点命中，然后按需要读寄存器、内存、调用栈，或用 `step`/GDB `step`、`next` 单步。未命中时报告仍在运行或超时，不将超时当作命中。一次性断点、条件断点和数据观察点可分别用 GDB 的 `tbreak`、`break ... if ...`、`watch` 命令；先检查该目标和调试会话是否支持。

结束时按用户对运行/暂停状态的要求处理目标。用 `info breakpoints` 找到本次创建的编号，并以 `gdb_command({"command":"delete <编号>"})` 清理；`clear_breakpoints` 会清除**全部**断点及硬件比较器，包括旧会话遗留状态，仅在用户要求清空或确定独占该调试会话时调用。需要结束本次启动的 GDB 服务时先清理断点，再断开并停服。

交付诊断时区分直接读到的值、由符号/手册支持的解释，以及仍需实验验证的推断。
