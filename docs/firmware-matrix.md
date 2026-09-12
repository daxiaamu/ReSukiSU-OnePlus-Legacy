# 固件登记

从维护者 ROM 归档只读提取，并补充下载官方 8 Pro OxygenOS 末版；原始 NAS 文件未修改。对应原厂 boot 仅保存在本地工作目录，仓库提交提取的内核配置、来源 URL 和哈希。

| 机型 | ColorOS | OxygenOS | 状态 |
| --- | --- | --- | --- |
| OnePlus 8 Pro | IN2020_13.1.0.190(CN01) | IN2023_13.1.0.591(EX01) | 编译验证中；未真机验证 |
| OnePlus 8 | IN2010_13.1.0.190(CN01) | IN2013_13.1.0.593(EX01) | 编译验证中；未真机验证 |
| OnePlus 8T | KB2000_14.0.0.602(CN01) | KB2001_14.0.0.1311(EX01) | 编译验证中；未真机验证 |
| OnePlus 9 Pro | LE2120_14.0.0.1901(CN01) | LE2121_14.0.0.1902(EX01) | 编译验证中；未真机验证 |
| OnePlus 9 | LE2110_14.0.0.1901(CN01) | LE2111_14.0.0.1902(EX01) | 编译验证中；未真机验证 |
| OnePlus 9R | LE2100_14.0.0.605(CN01) | LE2101_14.0.0.2401(EX01) | 编译验证中；未真机验证 |

9R ColorOS：A-only / BLOCK OTA，可从 ZIP 直接提取 boot.img。OxygenOS：A/B / payload.bin。
一加 8/8 Pro 的上述 ColorOS 原厂 boot 哈希相同；一加 9/9 Pro 的对应 ColorOS 与对应 OxygenOS 原厂 boot 分别相同。仍按机型独立分支输出。
原厂内核 4.19.157-perf+；9/9 Pro 为 5.4.254-qgki-gd2a1055adeb0。各完整哈希见 devices/*.json。
同机型 ColorOS 与 OxygenOS 的内核配置及原厂导出符号/CRC 表均已比对一致。新内核仍需单独通过 scripts/check_module_abi.py 的检查才能打包；导出表一致不等于已通过运行时或真机验证。
