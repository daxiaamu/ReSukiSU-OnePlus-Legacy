# OnePlus 9RT

独立分支 `oneplus-9rt`，代号 `martini`，SM8350 / Linux 5.4.254。使用 ReSukiSU 最新主线、Manual Hook 和 `-daxiaamu` 后缀，未集成 SUSFS。

- ColorOS：`MT2110_14.0.0.2701(CN01)`，安全补丁 2025-12-01。
- OxygenOS：`MT2111_14.0.0.2702(EX01)`，安全补丁 2026-01-01。
- 两套 OTA 元数据均为 A/B，分别使用各自原厂 boot；不会复用 9 / 9 Pro 镜像。
- 原厂版本均为 `5.4.254-qgki-gac311b3399ae`，新编译版本追加 `-daxiaamu`。

两套原厂配置相同，13,842 个导出接口名称与 CRC 表相同。已从原厂 ColorOS 内核恢复 protobuf-c 描述符，27 个消息、2 个枚举与本项目 SM8350 协议布局一致，沿用共用协议修复及 CFI 安全回调。保留原厂 CFI；原厂未启用模块签名。原厂读取记录见 [stock evidence](oneplus-9rt-stock.json)。

9RT 官方源码中的 S3908 已包含单击事件 `0x10` 解码及单击／双击坐标读取，主机 C 解码测试通过 1,024 例；无需重复移植手势补丁。

当前状态：原厂镜像与配置已提取，源码补丁通过应用检查，正在接入完整编译。尚未真机验证，既有 v0.1.0-r2 Release 不包含 9RT。最终 boot 封装必须通过本项目完整导出 CRC、镜像组成及构建来源检查。
