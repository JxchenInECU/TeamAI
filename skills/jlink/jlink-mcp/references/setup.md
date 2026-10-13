# 团队 J-Link MCP 安装与成员配置

## 共享内容与依赖

团队分发 `jlink-mcp` skill 和名为 `jlink` 的 stdio MCP 定义。服务程序由成员安装，不上传或分发 SEGGER 二进制、驱动、固件、读回文件、日志、探针序列号或账号凭据。

- Node.js 20+ 与 npm（TeamAI 要求 Node.js 20+；本次配置在 Node.js 24 上验证）。
- TeamAI CLI 0.27.0 或兼容新版本，以及团队仓库访问权限。
- npm 包 `jlink-mcp@0.7.0`，固定为此次检查的版本；无需 VS Code 即可使用 stdio 服务。
- SEGGER J-Link Software and Documentation Pack，安装支持目标器件的版本及 USB 驱动。成员自行遵守 SEGGER 授权条件。
- Python 3.10+：仅运行 `scripts/intel_hex.py` 时需要，无第三方 Python 依赖。
- 可选：源码级调试需要 `arm-none-eabi-gdb` 或兼容 GDB，以及与目标镜像匹配的 ELF；外设符号解码需要匹配芯片的 SVD。
- 实际硬件操作还需要适配的 J-Link 探针、线缆、正确供电和目标板。

上游：[jlink-mcp](https://github.com/Klievan/jlink-mcp)，[SEGGER 下载](https://www.segger.com/downloads/jlink/)。

## 安装程序

```text
npm install --global jlink-mcp@0.7.0
npm root --global
```

记下第二条命令的结果。MCP 入口是该目录下的 `jlink-mcp/out/mcp/standalone.js`。团队使用 `node` 直接启动该文件，避免依赖 Windows 的 `.cmd` 包装器，也不在每次启动时自动下载最新包。若已有独立安装，可直接使用它的入口，但先核实版本为 0.7.0。

## 本机变量（不提交到团队仓库）

团队 `env/env.yaml` 仅声明默认值；`mcp/mcp.yaml` 引用 `${TEAMAI_JLINK_*}` 占位符。TeamAI 同步时将成员的值写入该成员本机 MCP 配置。

| 变量 | 默认值 | 成员填写内容 |
|---|---|---|
| `TEAMAI_JLINK_NODE` | `node` | PATH 中的 Node 命令，或 node 可执行文件绝对路径 |
| `TEAMAI_JLINK_ENTRY` | 空，必须设置 | `jlink-mcp/out/mcp/standalone.js` 的绝对路径 |
| `TEAMAI_JLINK_INSTALL_DIR` | 空，必须设置 | SEGGER J-Link 安装目录 |
| `TEAMAI_JLINK_DEVICE` | `Unspecified` | 可保留未指定；每次操作前查明实际器件并用 `set_device` 设置 |
| `TEAMAI_JLINK_INTERFACE` | `SWD` | 按实际板卡选择 SWD 或 JTAG |
| `TEAMAI_JLINK_SPEED` | `4000` | 连接速度，单位 kHz；按实际目标调整 |

在已接入团队的目录中，由成员在自己的终端逐项输入：

```text
teamai env set TEAMAI_JLINK_ENTRY
teamai env set TEAMAI_JLINK_INSTALL_DIR
```

需要调整其他值时，同样运行 `teamai env set <变量名>`。这些值仅保存在成员本机；不要使用 `teamai env add KEY <个人路径>`，后者修改共享默认值。不要把整个 AI 工具配置或本机 TeamAI 私有配置提交到团队仓库。

未设置必需路径时，TeamAI 会提示缺失变量并暂缓安装 MCP；skill 仍可同步。填好后执行：

```text
teamai pull
teamai mcp list
teamai doctor
```

重启/重新加载 AI 工具的 MCP 服务配置。已有同名 `jlink` 服务时，TeamAI 默认保留个人配置并报告冲突；不要直接使用全局 `--force`。先备份并核对该条目的启动参数、工具审批策略和其他本机扩展，再按需要迁移。共享配置不下发自动批准硬件操作的策略。

## 连接验证与边界

先检查服务启动和 MCP 工具发现，再在用户要求连接硬件时使用 `get_config`、`search_devices`、`set_device`、`check_setup` 验证本次目标。安装成功不等于探针连接或下载校验成功。多探针环境需明确选择探针；本模板不固定任何人的序列号。

服务启动、TeamAI 同步和 skill 加载均不授权擦除、下载或运行目标。具体硬件操作遵循 SKILL.md 和相应参考文件。

## 分发范围

当前配置位于共享根目录，供整个团队使用；路径由每个成员配置。将来若限定项目，应把 skill、MCP 和 env 一并移入对应命名空间，并在 `manifest/projects.yaml` 的 `resources.skills`、`resources.mcp`、`resources.env` 中同时声明。
