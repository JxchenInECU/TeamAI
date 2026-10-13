# ECUC 基线往返校验

适用：改变硬件对象数组、choice 子容器或跨模块引用前。先从**当前安装的 S32DS/组件版本**导出原 MEX 的完整 ECUC（通常为 `*.ecvd`），在独立工作区和工程副本中不修改数据地导入，再从导入结果导出 ECUC。保持版本检查开启；工具若报告版本不兼容，应停下查实际组件来源，不用忽略版本参数硬闯。

1. 记录 S32DS、插件、RTD/SDK 版本、原 MEX 与各 ECUC 文件哈希；原导出为 `before`，重新导出为 `after`。两个目录都必须是同一工具范围的完整输出，不用手造的 ARXML 代替基线。
2. 先查看原始 ECUC：`AR-PACKAGE/SHORT-NAME`、`ECUC-MODULE-CONFIGURATION-VALUES/SHORT-NAME`、首层 `ECUC-CONTAINER-VALUE/SHORT-NAME`（config_set），以及 `DEFINITION-REF`、`VALUE-REF` 的绝对前缀。显式识别 `PARAMETER-VALUES`、`REFERENCE-VALUES` 等 list 包装，以及同一 choice 下实际选中的容器类型。不能把未知节点、属性、重复项或引用静默跳过。
3. 运行 `scripts/ecuc_roundtrip.py before after`。它严格比较全部 XML 元素、属性、文本、容器顺序、module/config_set 名与引用，忽略格式空白和属性顺序。缺文件、非法引用、未知结构发生变化均失败；不会因为识别不了某个新节点就跳过。人工复核工具自身可能重排的差异，未解释前不写入目标配置。
4. 基线通过后再构造本次候选，按当前 XDM/组件模型确认 list/choice/ref 的具体编码，并在新一轮独立目录导入验证。不能从一个车型、芯片或组件版本的 XML 猜另一个版本的枚举或引用前缀。

此比较器只证明**两轮工具导出在严格 XML 结构上相同**，不替代 Config Tools 校验、代码生成、构建或板端测试。若当前工具导出不稳定以致比较失败，应报告具体差异并保持候选未写回；不要放宽为“忽略未知节点”。
