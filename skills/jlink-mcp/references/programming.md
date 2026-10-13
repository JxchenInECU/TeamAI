# 下载、擦除与校验

## 确定本次目标

优先使用已暴露的 `jlink` MCP 工具；若工具未出现在当前会话，检查服务器配置并通过其 stdio 接口测试，明确记录实际调用路径。当前安装的 `jlink-mcp` 0.7.0 支持 `list_devices`、`search_devices`、`set_device`、`check_setup`、`get_config`、`probe_command`、`flash` 和 `erase`。升级后以实际工具说明为准。

1. 从用户给出的芯片型号、板卡标识、工程配置和器件资料确定目标。`list_devices` 找探针，`search_devices` 找 J-Link 支持的精确器件名。不能用旧的 `JLINK_DEVICE` 配置推断当前芯片。对选定器件执行 `set_device`，随后用 `check_setup`、`get_config` 和可用的只读目标信息核实连接、接口、电压及内核；多探针时核实序列号。
2. 明确镜像文件和目标内存：Intel HEX 可用 `scripts/intel_hex.py inspect` 检查校验和与地址段；BIN 必须有可信基址；ELF 根据可加载段判断范围。把地址与**本次芯片**的 Flash 布局及保留区对照。若镜像涉及 OTP、配置/密钥、HSE/安全区域，确认目标板状态和用户预期再操作。
3. 将擦除范围限制到完成任务所需的扇区。固件下载通常由 J-Link 的 `loadfile` 自行处理所需扇区；不要自动附加整片擦除。实际扇区可能扩展到请求范围之外，依器件扇区边界核对邻近数据。

## 调用与证据

- `flash({filePath})` 可下载 HEX/ELF；BIN 另传 `baseAddress`。在当前版本的 J-Link 后端，它执行 reset、halt、loadfile、reset、go，因而目标会重启并运行。路径使用可读的绝对路径。
- `erase({})` 调用 J-Link 无范围的 `erase`，会擦除目标 Flash；只在明确需要整片擦除时使用。局部擦除可调用 `probe_command({commands:["erase 0x起始地址 0x结束地址"]})`，并检查原始回显里的实际 Range、扇区和 `Erasing done`。SEGGER Commander 的 `Erase [<SAddr> <EAddr>]` 支持范围擦除。
- 不以 MCP 返回的 `Flashed ...` 或 `Chip erased` 文本单独判定成功。检查原始 J-Link 日志中的错误和校验结果；局部擦除后读回抽查起止位置。下载后优先使用 J-Link `savebin <文件> <地址> <字节数>` 读回，再比对镜像有效字节。Intel HEX 可用 `scripts/intel_hex.py verify`。跨越巨大空洞的镜像分段读回，不要一次导出整个地址跨度。
- 如果编程、擦除或比对失败，保留日志并定位器件/接口、供电、保护、Flash 算法、地址或文件问题。只在原因明确、目标和数据范围仍正确时重试。不要用解锁或整片擦除作为泛用恢复步骤。

示例（其中地址只表示**已核实的目标区域**，不能复制到另一型号）：

```text
probe_command: {"commands":["erase 0x00400000 0x0041FFFF"]}
flash: {"filePath":"C:\\path\\firmware.hex"}
probe_command: {"commands":["savebin C:\\path\\readback.bin 0x00400000 0x20000"]}
python scripts/intel_hex.py verify C:\path\firmware.hex --segment 0x00400000 C:\path\readback.bin
```

`erase` 和 `loadfile` 的命令语义以 [SEGGER J-Link Commander 文档](https://kb.segger.com/J-Link_Commander) 为准。
