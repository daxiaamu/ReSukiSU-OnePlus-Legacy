# 原厂驱动兼容性检查

完整内核导出表比较保存在 `abi-report.json`。一加 9 / 9 Pro 要求原厂导出名称与 CRC 全部匹配。

SM8250 另有两项触屏回调：`preconfig_power_control`、`reconfig_power_control`。公开源码的私有 `touchpanel_data` 布局与末版原厂有差异；这些回调及其内建调用方使用同一套公开头文件编译。仅当其余导出接口全部匹配、没有缺失导出，并且原厂 vendor、odm 中所有驱动模块均不引用这两项接口时，封装流程才允许保留这项内建实现差异。

核验步骤：

1. 从对应完整 ROM 只读提取 vendor、odm 分区到原厂 boot 所在目录的 `partitions/`。9R ColorOS 需还原 ZIP 内 Brotli 数据与 transfer list；不可按 A/B payload 处理。
2. 使用 erofs-utils 的 `dump.erofs` 遍历两个分区的全部目录，记录每个原厂 .ko 的路径与 SHA-256。脚本不会修改分区镜像。
3. 解析原厂模块的 `__versions`、导出符号及 vermagic，核对内核依赖和模块之间的依赖。分区、模块、原厂 boot、目标 Image 均绑定校验和。
4. 封装时重新核验原厂模块，保留完整导出差异报告，以及 `module_crc_check` 检查结果。不会替换或伪造 CRC。

Linux 示例：

```sh
python3 scripts/inventory_stock_modules.py \
  --stock-dir .work/stock/oneplus-8/coloros \
  --dump-erofs /path/to/dump.erofs
python3 scripts/check_stock_modules.py \
  --stock-dir .work/stock/oneplus-8/coloros \
  --built-dir out/oneplus-8/coloros
```

目录末两级应为机型和系统，例如 `oneplus-8/coloros`。清单脚本按公开机型配置核对原厂 boot SHA-256，不读取 NAS 路径记录。分区文件系统清单、驱动哈希和检查结果可用于复核。

这些是静态兼容性检查，不代表开机、触控、指纹、相机、无线网络或休眠已在真机测试。公开源码与原厂内核可能存在未公开的功能差异；产物应标记为实验版。
