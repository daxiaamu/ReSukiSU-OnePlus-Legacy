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

公开源码将十个原厂 `CONFIG_OPPO_*` 配置改名为 `CONFIG_OPLUS_*`；构建时映射名称，并检查配置值保留。兼容补丁修正 Clang 交叉汇编器前缀、rootguard 汇编对象的配置条件和调度函数的无参数原型。SM8150 源码没有其他平台的 protobuf data_module，因此不套用其协议补丁。

S3908 触控驱动补齐 `STAP_DETECT (0x10)` 到 `SingleTap` 的事件转换及单击／双击坐标解码，对实际 C 解码函数的 1,024 个测试用例通过。但这八套原厂配置没有启用 S3908（`CONFIG_TOUCHPANEL_SYNAPTICS_TCM_ONCELL`），该源码补丁不代表实际设备的触控已验证；构建保留原厂 S3706、Novatek 和 Samsung 驱动选择，触屏实测仍需对应设备完成。

## 验证状态

八套原厂内核的配置相同，11,964 个导出接口的名称与 CRC 也相同；模块信任证书并不全部相同，必须分别构建。已完整扫描各固件 vendor、odm 分区，每套 32 个模块的原厂依赖 CRC、版本和 PKCS#7 签名检查通过。

新内核仍在 Actions 编译和兼容性验证中，尚未生成可分发成品，未完成真机验证，也不包含在现有 v0.3.0 Release 中。配置状态保持 `hold`，防止未验证镜像进入打包流程。
