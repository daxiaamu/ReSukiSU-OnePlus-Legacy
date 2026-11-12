# OnePlus 7 / 7 Pro / 7T / 7T Pro

四款机型分别使用 `oneplus-7`、`oneplus-7-pro`、`oneplus-7t`、`oneplus-7t-pro` 分支。以 ColorOS 为主，OxygenOS 为辅；以下是从原厂 OTA 元数据核实的目标版本。

| 机型 | ColorOS 12.1 | OxygenOS 12.1 |
| --- | --- | --- |
| 7 | GM1900_11_H.40 | GM1901_11_H.41 |
| 7 Pro | GM1910_11_H.40 | GM1911_11_H.41 |
| 7T | HD1900_11_F.22 | HD1901_11_F.22 |
| 7T Pro | HD1910_11_F.22 | HD1911_11_F.22 |

八套固件均为 A/B，安全补丁日期为 2022-12-05，原厂内核版本为 `4.14.180-perf+`。原厂 boot 均为 100,663,296 字节，各自的 SHA-256、OTA 地址、配置与模块证书保存在 `devices/*.json` 中，分区扫描和导出表摘要见 [原厂证据](oneplus-7-stock.json)。不同机型和系统必须使用对应 boot。

## 源码与修改

使用 OnePlus 官方 SM8150 Android 12.1 源码：

- 内核：`OnePlusOSS/android_kernel_oneplus_sm8150`，提交 `180d787684d5965be5145bcfbf666ed427b4ea18`。
- 驱动：`OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8150`，提交 `993439581252cf872cd3c184ed3eb9e0f286f4c3`。
- 两个仓库的分支均为 `oneplus/sm8150_s_12.1_op7pro`。

每次 Actions 构建解析 ReSukiSU 官方默认分支的最新提交，使用适合 Linux 4.14 的 Manual Hook，追加 `-daxiaamu` 内核后缀，未集成 SUSFS。

SM8150 使用校验和固定的 AOSP GNU ld 2.27。原厂 GSI 的 `gsi_write_channel_scratch` 导出 CRC 为 0，公开源码同样未生成该符号的 CRC；新版链接器拒绝这个弱符号重定位。已用实际 GSI 对象的独立链接探针验证旧版链接器保留原厂的 0 值；未重写 CRC，也未关闭模块版本检查。链接器来源、版本和 SHA-256 记录在 `tools.lock.json` 及构建清单中。

公开源码将十个原厂 `CONFIG_OPPO_*` 配置改名为 `CONFIG_OPLUS_*`；构建时映射名称，并检查配置值保留。兼容补丁修正 Clang 交叉汇编器前缀、rootguard 汇编对象的配置条件，以及调度、触控、显示和充电函数的无参数原型。电机驱动删除未使用的模式中间值，保留原有 PWM 计算公式及硬件设置调用；vservices 删除无用的普通指针读取，保留消息处理逻辑。SM8150 源码没有其他平台的 protobuf data_module，因此不套用其协议补丁。

公开源码还将原厂的部分 `oppo` 类型、字段和导出接口改为 `oplus` 名称。特别是调度任务里的 jank 类型名称，会连带改变大量接口的 genksyms CRC。`configs/sm8150-stock-abi.h` 在实际 C 编译及 genksyms 处理时统一恢复这些旧标识符，不重写 CRC，不隐藏结构布局差异，也不关闭模块校验。头文件校验和写入构建清单，封装时拒绝使用修复前的构建。

已从实际导出文件提取预处理结果并重放 genksyms，确认恢复两个 jank 标识符后，模块、互斥锁、调度、平台驱动和 SLUB 五组共 86 个导出的 CRC 全部匹配原厂。显示状态的两个枚举返回接口也已单独核对，最终完整镜像通过下述全部导出和原厂模块检查。

其余接口差异也分别定位：关闭 mountguard 后仍包含原厂 kevent 头文件，以保留挂载接口的类型可见性；显示面板恢复三个旧类型／字段名称。触控统计恢复原厂公共事件枚举的 0–16 编号，将新增的手势读取、低中断率统计事件安排在独立的内部扩展编号，保留现有处理函数。原厂函数反汇编的分派上限为 16，恢复公共枚举后的 `tp_healthinfo_report` CRC 为原厂的 `0xa56a839d`；CI 通过实际 C 编译检查原厂事件编号、枚举宽度及扩展编号不冲突。新增统计事件继续调用原有处理函数，触控坐标和硬件时序不受这项编号修复影响。

初始核心类型重放的输入哈希与结果见 [ABI 诊断记录](oneplus-7-abi-replay.json)。完整镜像的导出检查仍是最终封装条件，未新增 ABI 差异豁免。

S3908 触控驱动补齐 `STAP_DETECT (0x10)` 到 `SingleTap` 的事件转换及单击／双击坐标解码，对实际 C 解码函数的 1,024 个测试用例通过。但这八套原厂配置没有启用 S3908（`CONFIG_TOUCHPANEL_SYNAPTICS_TCM_ONCELL`），该源码补丁不代表实际设备的触控已验证；构建保留原厂 S3706、Novatek 和 Samsung 驱动选择，触屏实测仍需对应设备完成。

## 验证状态

八套原厂内核的配置相同，11,964 个导出接口的名称与 CRC 也相同；模块信任证书并不全部相同，必须分别构建。已完整扫描各固件 vendor、odm 分区，每套 32 个模块的原厂依赖 CRC、版本和 PKCS#7 签名检查通过。

构建会核对全部原厂已启用配置，经名称映射后只允许内核版本后缀和模块证书路径发生预期变化。公开驱动新增且默认开启的 Novatek 手写笔选项不在原厂配置中，已显式关闭；ReSukiSU 的新增选项单独保留。

八份新内核均由各机型分支的 Actions 编译，使用上游提交 `548d1dda060ca198823d8808804d01f5209ef4a9`。每份 11,964 个原厂导出的名称和 CRC 全部匹配，32 个原厂模块的依赖、版本与签名检查通过；封装后重新解包，核对内核哈希、原厂 ramdisk、DTB、其他非内核组件和启动头，检查镜像大小。

八份 `boot.img`、对应 ZIP、校验表及官方 Actions 管理器 APK 已发布于 [v0.4.0 实验版](https://github.com/daxiaamu/ReSukiSU-OnePlus-Legacy/releases/tag/v0.4.0)，本地 `out/` 同时保留。管理器为 v4.2.0-rc3（35259）、ARM64，与内核使用同一上游提交；APK 未修改、未重新签名。构建链接和校验值见 [成品记录](oneplus-7-artifacts.json)。

配置状态为 `experimental`，尚未完成真机验证；开机、解密、触控、升降摄像头、指纹、无线网络、休眠及 Root 授权仍需对应设备实测。这批镜像在 v0.4.0 单独发布，原有七款机型的 v0.3.0 Release 保持不变。
