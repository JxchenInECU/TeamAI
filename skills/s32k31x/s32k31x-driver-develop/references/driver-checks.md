# 按需求使用的配置检查表

所有候选外设先查该 **S32K31X 具体型号** 的 feature comparison / chip-specific 信息。下表是检查项目，不是断言所有型号都具备这些资源。

## 共同依赖

确认芯片/封装、实际板级接线、驱动层、RTD 版本和使用的配置集。记录 `外设实例 → kernel clock → 引脚 → IRQ/DMA → 触发 → 初始化/调用`。核对生成代码是否进入当前构建及启动流程；默认 init、手动 init 和 boot init 的责任不能重叠或遗漏。

涉及具体硅片行为时先按 [本地 mask set 勘误](local-sources.md#本地-mask-set-勘误)确认实际 mask 和适用 PDF；仅在具体 erratum 的触发条件成立时纳入配置或 workaround。mask 未知则说明适用性未确认。

修改字段前，从目标型号及当前组件版本的枚举/资源表取得**该字段**的合法候选值，并记录来源。时钟树节点名、UI 显示标签、MCAL 参数枚举和寄存器名不能因拼写相近而互换。例如 `CORE_CLK` 作为时钟树节点名，不能据此推断某个 `McuClockReferencePoint` 字段接受同名枚举；应查询该字段的 XDM/组件模型、当前工具资源或同版本有效导出。

初始化次序从同版本文档和项目推导：时钟与模式/门控就绪、引脚状态安全、驱动及缓冲区初始化、安装中断/DMA处理链、最后启用请求/触发。不是所有 API 都能套用同一固定顺序。AUTOSAR Mcu/Port 等与 IP 层 Clock_Ip/Siul2_Port_Ip 等按项目选择，不混配同一硬件的控制权。

## 时钟与模式

- 板上 FXOSC/SXOSC 频率、模式和器件是否真实存在；不能把示例的 16/40 MHz 当作客户晶振值。
- 从源到 PLL、mux、分频、总线、外设 kernel clock 逐级列实际频率；查目标型号、电压/温度和工作模式下的限制。
- CPU、总线、Flash 时序与外设时钟分别核对；不能只验证 core 频率。
- 门控、切源前后时序、PLL lock/超时、FIRC/SIRC 精度与通信容差、RUN/低功耗/唤醒后的恢复。
- `clock_outputs` 数值和生成的寄存器/配置结构交叉验证。若改公共源，重新检查所有消费者。

## Pins / SIUL2 / GPIO

- 查对应封装是否真正引出 pad；区分球号/脚号、PTx 标号、MSCR 索引及外设信号。
- 输出复用和输入 IMCR 路径分别核对；输入使能、输出使能、上拉下拉、开漏、驱动强度、转换速率以电气需求和资料为准。
- 检查多个消费者争用同一 pad、多个 pad 对同一输入的选择冲突、调试/晶振/启动脚占用。
- GPIO 初始电平、片选/收发器使能的有效极性、复位和低功耗状态、防毛刺顺序。
- 不给数字 IO 或模拟输入假定统一耐压；查对应电源域和引脚类别。

## LPUART / UART

实际 kernel clock、波特率、数据位/停止位/校验、TX/RX 路由、FIFO、轮询/中断/DMA、异步缓冲区寿命与回调。按当前 IP 的 OSR/SBR 定义求可达速率并给误差，不把 UI 期望值当实际速率。核对低过采样限制、发送完成与缓冲区空的区别以及收发器/电平转换条件。

## FlexCAN

实例与时钟源、Classic/FD、仲裁段和数据段位时序、BRS、采样点、SJW、传播延时和收发器能力；Classic 不配置 FD 数据阶段。核实时间段是物理 TQ 还是寄存器 N-1 编码。名义速率可用 `fCAN / (prescaler × total_TQ)` 检查，但 prescaler/segment 的允许范围来自目标寄存器与 RTD 字段定义。检查 MB/FIFO 内存分配、过滤器、IRQ、bus-off 恢复、TX/RX 引脚、STB/EN 和终端电阻。编译通过不能证明总线时序满足实物条件。

### CAN 与 CanIf 接入

- 先确认配置工程与实际业务工程的角色、CanIf 供应商/版本及配置生成方式。S32DS/RTD 可提供用于依赖校验和代码生成的简化 CanIf；若 CAN 生成依赖该组件，应保留它，不将其配置结构直接当作实际完整 CanIf 的结构。
- 在 S32DS 3.6.6 / RTD 5.0.0 D2408 的本地配置工程中曾观察到 `HohToRxPduMappingPtr[HRH]` 仅指向一个 RxPdu。这是该简化实现的行为，不能得出“CanIf 每个 HRH 只能映射一个 RX PDU”的通用结论。用户确认实际工程使用完整 CanIf 时，以该实现及其配置工具为准。
- 完整 CanIf 的 BasicCAN HRH 可由多个 RxPdu 共享，通过 HRH、实际 CAN ID 和帧类型进行软件过滤与分发。FIFO 共用一个 HRH；范围接收 MB 也可按 BasicCAN 处理；单 ID 专用 MB 可按 FullCAN 处理。启用软件过滤并逐项核对实际供应商的 HRH/RxPdu 引用、ID、Classic/FD、标准/扩展帧及长度配置。
- MB 与 FIFO 接收统一使用 `CanIf_RxIndication(const Can_HwType *, const PduInfoType *)` 等当前版本匹配的标准接口；发送使用 `CanIf_Transmit` → `Can_Write`/`Can_43_FLEXCAN_Write` → `CanIf_TxConfirmation`。CanIf 使用逻辑 HRH/HTH，物理 MB 重排不应被误写成 CanIf 句柄变化。
- 不因简化组件能力不足而自动新增绕过完整 CanIf 的应用分发层。已有 LPDU callout 若返回 FALSE 会阻断正常 CanIf 接收，应按实际接入方案清理；保留监测 callout 时验证其返回值和数据生命周期。
- 实际固件只链接一套 CanIf 实现及匹配的头文件/配置。S32DS 生成的简化 CanIf 文件不直接覆盖业务工程的完整 CanIf；核对回调签名、ControllerId、HRH/HTH、FD 标志和 TxPdu/swPduHandle 映射。接收指针在回调后可能被复用，上层异步处理须及时复制数据。

接口与软件过滤依据：[AUTOSAR CAN Interface R21-11](https://www.autosar.org/fileadmin/standards/R21-11/CP/AUTOSAR_SWS_CANInterface.pdf) 7.8、7.20；实际接口和参数仍以目标 CanIf 版本为准。

## LPSPI / LPI2C

- SPI：主/从、CPOL/CPHA、数据宽度、位序、SCK 实际频率及误差、PCS 极性/保持、帧间和片选延时、引脚方向、DMA/IRQ。
- I2C：开漏、板级上拉/电容、电压域、上升时间、滤波、时钟高低周期、地址格式、重复起始、clock stretching、超时和总线恢复。不要把枚举的 fast mode 当作电气时序合格证。

## ADC 与触发

先确认 ADC 实例和封装通道，模拟引脚模式、参考电压、模拟供电、信号阻抗与采样时间。区分目标采样率、ADC kernel clock、采样窗口和转换总时长。检查分辨率、校准、扫描/队列、软硬件触发、BCTU/TRGMUX（若目标支持）、结果存储、DMA 完成与溢出。硬件触发链逐段验证“定时器 → 路由 → ADC → DMA/IRQ”。

## 定时器 / PWM / 输入捕获

先核对模块实际存在。按项目涉及检查 PIT/STM/eMIOS 等的时钟、预分频、计数模式、周期/占空比/分辨率和误差。eMIOS 时基 master bus 和通道依赖不能省略。中心对齐、边沿对齐、死区、互补输出、故障输入、更新时刻各自查模式定义，不能共用一个未经确认的周期公式。捕获考虑回绕和时间单位。

## DMA / 中断 / OSIF

- DMAMUX request ID 与实例、eDMA 通道、源/目的地址、宽度/对齐、minor/major loop、触发和链接关系。
- 缓冲区可访问性、MPU/cache 属性、一致性及完成后的所有权；不能仅通过 volatile 解决 DMA cache 一致性。
- IRQ 号从芯片表与该 RTD 头文件核实，向量名/ISR 和驱动处理函数一致；优先级位数、RTOS 可调用级别、是否安装并启用 NVIC、共享中断处理。
- OSIF 的计时源、实际频率、超时单位及低功耗行为；不要在系统 tick 未运行时使用依赖它的超时。

## 看门狗 / Flash / 低功耗

只对本次需求检查 SWT 超时/窗口/服务与调试行为；Flash 的链接分区、对齐、擦写粒度、执行位置、并发与中断约束；唤醒源、保持资源和恢复顺序。配置分析不执行擦写/永久锁定。涉及安全启动或 HSE 时明确当前资料与授权边界，不能推测生命周期和密钥状态。
