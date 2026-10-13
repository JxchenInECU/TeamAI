# MEX 解析、差异和修改

## 实际观察的结构

本机官方示例为带命名空间的 XML，常见根为：

```xml
<configuration name="..." version="15" uuid="..."
 xmlns="http://mcuxpresso.nxp.com/XSD/mex_configuration_15">
  <common>
    <processor>...</processor>
    <package>...</package>
    <mcu_data>PlatformSDK_S32K3</mcu_data>
    <cores selected="M7_0">...</cores>
  </common>
  <tools>...</tools>
</configuration>
```

这只是已观察的版本，不要求把其他工程强制变为 version 15。解析保留 namespace 和版本，不删除未知工具/节点。

- `tools/pins`：`functions_list/function` 下的路由、电气配置，`generated_project_files` 下的生成文件记录（见下文的输出一致性检查）。
- `tools/clocks`：`clock_configurations/clock_configuration`，包括 `clock_sources`、`clock_outputs`、`clock_settings` 等。保存的输出频率可能是派生显示值，不等于实际硬件配置。
- **Peripherals 的 XML 元素实际常为 `periphs`**，不是 `peripherals`；以工具 `name="Peripherals"` 辅助识别。
- `periphs/functional_groups/functional_group/instances/instance` 含 `name/type/type_id/mode/enabled`，配置位于 `config_set` 的 `struct/array/setting`，常见值为 `<setting name="..." value="..."/>`。
- 多个功能组/实例可能有相同 `setting name`。按完整祖先路径区分，不能对整个文件全局替换名字或数值。
- `enabled`、`update_project_code`、生成文件 `update_enabled` 独立检查。`dependencies` 是约束模板，不是实际校验输出；文本中出现 “not found” 不等于依赖已缺失。
- `.project`、`.cproject`、`.settings`、链接资源、SDK 组件选择和应用调用也影响最终构建。配置文件存在不证明生成代码被编译/调用。

## 只读检查

`mex_tool.py inspect` 输出芯片、封装、namespace、版本、工具、功能组实例、输出文件及其开关，并明确硬件与 Config Tools 校验尚未执行。`--query` 搜索带完整索引路径的属性与文本；该路径按同标签兄弟节点计数，描述当前位置，不承诺跨版本稳定。

`mex_tool.py diff` 比较 namespace、元素名、属性、非空文本与结构位置；属性顺序和格式空白不影响结果。默认不忽略 UUID、路径或其他属性。插入/重排节点可能带来多个位置差异，因此同时看文本 diff；不要把每个位置差异都当成独立功能变化。

写回前建立允许变化的**完整 XML 子路径与属性**白名单，比较原始基线和最终主 MEX。既要检查跨模块等价，也要检查目标模块内部未列入白名单的字段；不能把整个目标模块从比较中排除。若只计划改变 Can/CanIf 的对象数组，应逐项核对同模块的 `CAN_GENERAL`、位时间、控制器参数等未授权字段仍与基线一致。数组增删和顺序变化需按稳定对象标识复核，不能只靠位置差异放行。

## 生成文件清单与实际输出

`generated_project_files` 是配置保存的生成文件记录，可能继承旧 MEX 的名单或记录临时导出路径。它需要与当前生成器实际产物核对，不能单独作为最终输出位置和完整性的证明。

- 合并 MEX、改变功能组或生成方式后，核对各模块的文件集合、路径、更新开关和角色后缀；识别旧文件的退役/重命名以及新增文件的构建引用，不沿用原单组清单判断多组输出完整性。
- 对照 GUI Update Code/当前工具预览、正式保存的 MEX 和落盘文件，确认需要的文件存在且确实写入设计中的正式目录。发现输出关联到备份或暂存目录时，先查工程文件查找与隔离状态，不继续覆盖历史副本。
- CLI 导出的 MEX 在成为正式配置前单独审阅上述记录；不把带有临时输出位置的导出样本直接当作 GUI 工程配置交付。生成文件清单的修正也纳入 XML 路径白名单，保持无关模块参数与用户编辑不变。

## 修改选择

优先 S32DS UI；对已核实的少量现有 XML 值，可在工程副本上用精确文本补丁保留字节格式、注释、声明、换行和所有未知字段。

提供的 `mex_tool.py patch`：

1. 输入是 UTF-8 JSON 计划，包含原文件 SHA-256，以及一组 `old`/`new` 精确片段。
2. 每个旧片段必须仅出现一次且互不重叠，值来源需先由 Agent 核实；禁止用它猜字段。
3. 默认仅预演；`--output` 才写入一个**尚不存在的新 `.mex` 文件**。脚本不会原地覆盖工程。
4. 补丁前后验证 XML，可拒绝非 S32K31X 目标、目标型号/封装/core/SDK/格式版本改变；不做 schema、枚举、时序或依赖验证。
5. Agent 检查新文件差异后，在有基线/备份的工程中应用改动并重新加载工具。输出文件路径改变可能影响相对工程链接，不要直接在脱离工程目录的位置生成代码。

先对全部替换和 IRQ 等标识做存在性、唯一性、拼写及解析检查，失败时不写主文件。保留原 BOM、编码与逐行换行形式，禁止把 LF 文件统一改成 CRLF。候选输出先写同目录临时文件并完成写入，再原子提交为**新文件**；主 MEX 的最终替换也要在当前哈希未变化时按工程备份策略原子进行。PowerShell 中不要用含 XML 引号的 `python -c` 拼接脚本；用独立脚本、参数数组或 UTF-8 计划文件传参。

补丁适合已有属性值的小改动。添加外设、改变数组结构、增加跨模块引用、切芯片、升级组件时用工具编辑；不要手造 UUID 和引用以拼出完整配置。

不要在 GUI 持有未保存编辑时从磁盘覆盖 `.mex`。先协调保存/重新加载，防止旧内存状态把新配置覆盖。
