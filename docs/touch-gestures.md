# 息屏单击手势源码审查

2026-09-13，针对另一个 8T 移植项目发现的 S3908 单击事件漏解码，检查本项目六款机型在 `devices/*.json` 固定的 vendor 源码。结论针对本项目配置的 ColorOS / OxygenOS；不代表其他系统或面板已真机验证。

| 机型 | 设备树中的触控路径 | 本次结论与处理 |
| --- | --- | --- |
| 一加 8 | 19821 / 19855：Samsung S6SY771 | 三星驱动已有 `GESTURE_SINGLE_TAP` 和坐标解码。共用源码内编译启用的 S3908 仍缺处理，预防性补齐；不能据此认定一加 8 原来存在该故障。 |
| 一加 8 Pro | 19811：Samsung S6SY791，另有 S3908 节点 | 三星路径已有单击处理；补齐 S3908 路径，实际影响取决于面板及探测结果。 |
| 一加 8T | 19805：Synaptics S3908 | 确认缺失 `STAP_DETECT (0x10)` 到 `SingleTap` 的转换，已补齐。 |
| 一加 9R | 20828 / 20838：Synaptics S3908 | 确认同样缺失，已补齐。ColorOS 的 A-only 与 OxygenOS 的 A/B 分别封装，不改变分区结构。 |
| 一加 9 | lemonade-19825 / lemonadev-2080a：Samsung S6SY792 | 三星驱动已有单击事件与坐标解码，无需同类补丁。 |
| 一加 9 Pro | lemonadep-19815（含 T0）：Synaptics S3908 | 已有 `STAP_DETECT` 和从 `extra_gesture_info` 读取单击／双击起始坐标的逻辑，无需重复修复。 |

设备树证据位于 SM8250 vendor 仓库的 `vendor/qcom/proprietary/devicetree-4.19/<项目号>/kona-mtp.dtsi`，以及 SM8350 的 `vendor/qcom/proprietary/devicetree/oplus/lemonadev/*.dtsi`。驱动位于 `vendor/oplus/kernel/touchpanel/oplus_touchscreen/`。同一源码包含多个设备节点，不能把已编译驱动等同于实机实际使用的芯片。SM8350 额外编译的 v2 S3908 / S3910 解码也已有单击事件分支。

补丁补充事件常量和转换分支，并从 `extra_gesture_info[0..3]` 读取单击／双击起始坐标。集成在 `vendor-oneplus-8.patch`（8 Pro 共用）、`vendor-oneplus-8t.patch`、`vendor-oneplus-9r.patch`；现有编译与封装流程会记录、校验整个 vendor 补丁的 SHA-256。ReSukiSU 最新源码解析、`-daxiaamu` 后缀、原厂模块签名与 CRC 校验继续生效。

修复移植自 [8T 项目的 5314771](https://github.com/daxiaamu/ColorOS-16-17-Port-for-8T/commit/5314771)，其参考为 [OPPO SM8250 官方 Android 14 源码](https://github.com/oppo-source/android_kernel_modules_and_devicetree_oppo_sm8250/commit/f141bd5518945b3c887f1e48203368fff6be3af2)。本项目 SM8350 固定源码本身也具有同样的 S3908 处理。

## 验证与边界

`scripts/audit.py` 对全部七款固定源码检查补丁，然后调用 `scripts/check_s3908_gesture.py` 编译实际 C 解码函数。每款测试全部 256 个事件值 × 4 组数据，共 1,024 例：检查单击类型、单击／双击起始坐标，并逐字段比较其他事件修复前后的输出。加入 9RT 后，七款合计 7,168 例通过；同一测试已接入 Source and tooling checks Actions。

这是主机上的解码回归测试，不覆盖触控固件实际发包、休眠中断、Android AOD 策略或整机启动。修复已收录于 [v0.2.0](https://github.com/daxiaamu/ReSukiSU-OnePlus-Legacy/releases/tag/v0.2.0)，七款共 14 份镜像均已完成编译与封装检查，但尚未完成本版真机单击唤醒复测。旧版 v0.1.0-r2 不含本次手势修复。

9RT 的独立排查与成品记录见 [9RT 说明](oneplus-9rt.md)。
