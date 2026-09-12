# 9R 启动故障记录

9R 已报告停在 ColorOS 开机动画，尚未定位原因；暂停使用本批次 9R 镜像。OxygenOS 未确认受影响，同内核镜像一并暂停推荐。

用户报告：停在 ColorOS 开机动画。完整系统版本、刷入镜像及日志待确认。

原实验内核 SHA-256：

`80a4bf4fab2a4c44bf9e8ee1842d5cb6468a81ad45dc68be8ada14d7a4929b64`

静态模块 CRC、封装复检通过不能证明实际启动兼容。现有镜像保留用于复现，不应作为已验证成品。

配置复核发现公开源码未保留原厂 CONFIG_OPLUS_FEATURE_VIRTUAL_NET、CONFIG_TOUCHPANEL_ALGORITHM、CONFIG_TOUCHPANEL_FOCAL_FT3658U；编译器从原厂 Clang 10 换为 Clang 14。以上是待排查差异，并非已确定根因。

## Device evidence (2026-09-13)

ADB confirms LE2100_14.0.0.605(CN01); restoring the original kernel restores boot. Four system_server watchdog records at 03:38:17, 03:40:02, 03:41:46 and 03:43:30 all place the main thread in the SoundTriggerModule.attachToHal startup path. Samples include exception logging, ISoundTriggerHw.interfaceChain and getProperties_2_3. This identifies the blocking subsystem, not the underlying kernel defect.

Pstore contains KernelSU initialization and repeated Zygote exits; some bytes are damaged. Raw logs remain local and private. Previous-boot logcat is unavailable, so live failing-boot exceptions are still needed. The original-kernel log reaches SoundTrigger boot phase 1000.
