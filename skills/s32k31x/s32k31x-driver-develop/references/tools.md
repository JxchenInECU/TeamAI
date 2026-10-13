# 脚本用法

以下命令从技能目录运行，其他目录请用脚本绝对路径。Python 3.10+；`asset_query.py pdf` 需 `pypdf`，`xlsx` 需 `openpyxl`，其他脚本仅需标准库。Codex 中先用 `load_workspace_dependencies` 找具备依赖的 Python；JSON 和中文输入输出使用 UTF-8。

## 环境盘点

```powershell
python scripts/inspect_environment.py --install 'C:\NXP\S32DS.3.6.6' --project 'D:\workspace\MyProject'
```

`--install`、`--project` 可省略。结果列出启动器、插件、SDK manifest、设备和示例；先检查 `errors`，再使用统计结论。它不启动 IDE 或验证许可证。

## MEX 检查和差异

```powershell
python scripts/mex_tool.py inspect 'D:\workspace\MyProject\MyProject.mex'
python scripts/mex_tool.py diff 'D:\baseline\MyProject.mex' 'D:\workspace\MyProject\MyProject.mex'
```

`inspect --query Baud` 可筛选设置，但要核对完整路径和祖先实例；`diff` 是结构位置差异，不是硬件语义验证。`inspect` 可读取其他型号示例，`patch` 仅接受本技能范围型号。

## 精确补丁

先用 inspect 取得当前 SHA-256，并从文件中复制唯一片段。计划格式如下；这里的字段是**合成格式示例**，不是任何 RTD 的实际配置项，不能直接用于工程：

```json
{
  "sha256": "填入 inspect 返回的完整 64 位十六进制哈希",
  "replacements": [
    {
      "old": "<setting name=\"SyntheticExample\" value=\"old\"/>",
      "new": "<setting name=\"SyntheticExample\" value=\"new\"/>"
    }
  ]
}
```

```powershell
python scripts/mex_tool.py patch 'D:\workspace\MyProject\MyProject.mex' 'D:\work\change.json'
python scripts/mex_tool.py patch 'D:\workspace\MyProject\MyProject.mex' 'D:\work\change.json' --output 'D:\work\MyProject.candidate.mex'
```

不带 `--output` 为预演；输出必须是新文件。脚本拒绝重复/重叠匹配、过期哈希、非法 XML 和目标身份变化，不代替枚举/引用核查或 S32DS 验证。

## ECUC 基线往返比较

按 [ECUC 基线往返校验](ecuc-roundtrip.md) 由当前工具在隔离工程副本中分别完成原配置导出、无变化导入、再次导出后运行：

```powershell
python scripts/ecuc_roundtrip.py 'D:\work\before\board' 'D:\work\after\board'
```

只有返回 0 且 `status=pass` 才通过结构比较；工具配置与构建另行验证。

## S32DS CLI 运行证据

将本机帮助确认的完整命令作为参数数组传给包装器，指定目标模块、预期输出和实际版本。`--expected` 使用产物绝对路径，`--input` 保存输入快照。按 [CLI 操作模板](s32ds-cli.md) 设置 `$s32Console` 等变量后，例如：

```powershell
$cliArgs = @('-nosplash', '--launcher.ini', $s32Ini, '-consoleLog', '-application', 'com.nxp.swtools.framework.application', '-data', $workspacePath, '-HeadlessTool', 'Peripherals', '-Load', $mexPath, '-ExportMEX', $exportPath)
python scripts/s32ds_cli.py --evidence 'D:\work\evidence' --kind config --module Can --expected $exportPath --input $mexPath --version-label 'S32DS 3.6.6 / verified RTD version' -- $s32Console @cliArgs
```

每轮保留输入快照、`manifest.json` 和原始日志。`config_error`、`build_error`、`incomplete`、`timeout`、`needs_review` 均不算通过；缺失或未更新的预期产物也不算通过。解码有歧义时回看原始字节及工作区 `.metadata/.log`。

## PDF / XLSX / JAR 帮助

先用 `assets/data/` 中的章节索引缩小 PDF 页范围。以下 PDF/XLSX 使用技能内相对路径，命令从技能根目录运行；从其他目录调用时，将脚本和资料路径都基于 `SKILL.md` 所在目录解析。JAR 属于外部 S32DS 安装，示例路径须替换为当前机器已核实的版本与位置：

```powershell
python scripts/asset_query.py pdf 'assets/data/S32K3XXRM.pdf' --pages 38-44
python scripts/asset_query.py xlsx 'assets/data/S32K312_IOMUX.xlsx' --sheet 'S32K312_IO Signal Table' --find 'LPUART' --limit 8
python scripts/asset_query.py help 'C:\NXP\S32DS.3.6.6\eclipse\plugins\com.nxp.swtools.doc.uct_1.9.4.202607201458.jar' --entry 'resources-ide/support/help/en/topics/command_line_execution.html'
```

PDF `--pages` 用 1-based 页序，支持 `1,3-5`；表格抽取错列时回看原页。XLSX 无 Sheet 时列真实 Sheet，查询返回原始单元格、合并格来源及 `truncated`；公式不计算。用小行范围或 `--limit` 控制输出。

## 验证脚本

```powershell
python -m unittest discover -s tests -v
```

测试在临时目录操作合成 XML，检查字节保留、冲突拒绝与差异检测。它们不创建真实 S32DS 工程，也不证明配置可生成。
