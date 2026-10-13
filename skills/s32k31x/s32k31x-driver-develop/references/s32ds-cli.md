# S32DS CLI 操作

依据见 `local-sources.md` 的集成版帮助路径。以下是 **命令模板，未作为本技能制作过程的 S32DS 端到端验证**。执行时先替换变量为已确认的绝对路径，检查本机启动器/INI 和插件支持，收集 stdout/stderr、退出码和工作区 `.metadata/.log`。必要时只在工程副本验证命令。

每次运行使用新的 `run_id`：`staging` 放隔离工程副本和临时生成，`evidence/<run_id>` 放输入哈希、版本、命令、原始字节日志、状态与输出清单，`delivery` 仅放最终 MEX、必要生成文件和差异索引。不要把 staging 加入编译源；交付索引指向最终 MEX 和审阅 diff。可用 [脚本用法](tools.md) 的 `s32ds_cli.py` 保留每轮证据。CLI 返回 0 仍要检查目标模块的 `[TOOL] ... following error`、预期文件、进程结束和工作区日志；未覆盖到的诊断标为待人工复核。日志乱码时保留原始字节，摘要注明解码方式，不靠乱码片段下结论。

不要复用正由 GUI 打开的工作区，不能删除 `.metadata/.lock` 强行解锁。使用独立且无其他进程占用的工作区；串行操作同一工程。不要把 `<path>` 占位符直接提交执行。

## CLI 与 GUI 的验证边界

`-ExportSrc` 成功只证明本轮生成器向指定导出目录写出了文件，尚未覆盖 GUI Update Code 在正式工程中的已有文件定位、创建/删除、项目资源过滤和构建引用更新。合并 MEX、改变功能组或生成策略后，按用户的交付工作流分别验证；用户需要直接 GUI 使用时，仍须完成正式工程中的实际 GUI 更新，不能把 CLI 结果扩写为 GUI 已验证。

独立工作区与文件查找隔离分别检查：备份和暂存文件不参与编译，并不保证它们不会被 IDE 按同名文件查找到。隔离方式和 GUI 验收见 [生成策略变更与交付验收](s32ds-workflows.md#生成策略变更与交付验收)。CLI 保存/导出的 MEX 还须按 [生成文件清单与实际输出](mex-format.md#生成文件清单与实际输出)审阅输出记录，再用于正式交付。

PowerShell 公共变量示意（`$projectPath` 等由 Agent 使用真实路径设置）：

```powershell
$s32Install = 'C:\NXP\S32DS.3.6.6'
$s32Console = Join-Path $s32Install 'eclipse\s32dsc.exe'
$s32Ini = Join-Path $s32Install 'eclipse\s32ds.ini'
# 还需设置：$workspacePath、$projectPath、$mexPath、$exportPath、$buildTarget
```

导入已存在的工程：

```powershell
& $s32Console -nosplash --launcher.ini $s32Ini -consoleLog `
  -application org.eclipse.cdt.managedbuilder.core.headlessbuild `
  -data $workspacePath -import $projectPath
$importExitCode = $LASTEXITCODE
```

对单工具从 MEX 导出代码到新的暂存目录，`$toolName` 只选 `Pins`、`Clocks`、`Peripherals` 中本工程已启用的工具：

```powershell
& $s32Console -nosplash --launcher.ini $s32Ini -consoleLog `
  -application com.nxp.swtools.framework.application `
  -data $workspacePath -HeadlessTool $toolName `
  -Load $mexPath -ExportSrc $exportPath
$generateExitCode = $LASTEXITCODE
```

`-HeadlessTool` 不会自动启用被禁用的工具。不要为凑齐输出随意添加 `-Enable`。单工具导出不证明工程已完成所有工具生成、SDK 依赖同步或构建；每个已启用且受变更影响的工具都要验证。多工具链参数有各自作用域，先读取本机文档再拼接。

导入/更新配置并携带 SDK 组件依赖（会写工程，工程先通过上面的 CDT import 进入工作区）：

```powershell
$sdkPath = Join-Path $s32Install 'S32DS\software\PlatformSDK_S32K3'
& $s32Console -nosplash --launcher.ini $s32Ini -consoleLog `
  -application com.nxp.swtools.framework.application `
  -data $workspacePath -HeadlessTool Peripherals `
  -importProject $projectPath -sdkPath $sdkPath
$updateExitCode = $LASTEXITCODE
```

本机帮助描述此操作会校验和 Update Code，但仍要读实际日志及检查受影响 Pins/Clocks/Peripherals 输出；运行结果是最终证据。不要默认添加 `-overwriteWithSdkSources`、迁移到最新版本或禁用版本检查等参数。

构建已导入工程，`$buildTarget` 取 `.project` 项目名及 `.cproject` 的真实配置名，不猜 `Debug`：

```powershell
& $s32Console -nosplash --launcher.ini $s32Ini -consoleLog `
  -application org.eclipse.cdt.managedbuilder.core.headlessbuild `
  -data $workspacePath -build $buildTarget
$buildExitCode = $LASTEXITCODE
```

必要时使用 `-cleanBuild`，先确认仅涉及可再生构建产物。日志检查除了退出码，还核查实际构建的项目/配置、错误、输出 ELF/map 的新鲜度。没有输出文件时，即使进程返回 0 也不能报告生成成功。

CLI 参数如 `-MCU/-SDKVersion/-PartNum/-ExportMEX` 可以创建/导出工具配置；这些并不是已验证的新建完整 S32DS Application Project 接口。当前技能不提供伪造工程 XML 的“自动建工程”脚本。

GUI 路线先确认窗口可见、目标工程和 `.mex` 已加载、配置编辑可持续、保存/生成后有可读结果；有限次数观察仍达不到可持续操作状态时，若本机文档和现有权限支持，则在隔离工作区改走已验证 CLI，记录实际完成生成的是 GUI 还是 CLI。不要反复盲点或把仅启动进程当成 UI 可用。

