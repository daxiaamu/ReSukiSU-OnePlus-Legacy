# 9R 启动故障记录

9R 已报告停在 ColorOS 开机动画，尚未定位原因；暂停使用本批次 9R 镜像。OxygenOS 未确认受影响，同内核镜像一并暂停推荐。

用户报告：停在 ColorOS 开机动画。完整系统版本、刷入镜像及日志待确认。

原实验内核 SHA-256：

`80a4bf4fab2a4c44bf9e8ee1842d5cb6468a81ad45dc68be8ada14d7a4929b64`

静态模块 CRC、封装复检通过不能证明实际启动兼容。现有镜像保留用于复现，不应作为已验证成品。

配置复核发现公开源码未保留原厂 CONFIG_OPLUS_FEATURE_VIRTUAL_NET、CONFIG_TOUCHPANEL_ALGORITHM、CONFIG_TOUCHPANEL_FOCAL_FT3658U；编译器从原厂 Clang 10 换为 Clang 14。以上是待排查差异，并非已确定根因。
