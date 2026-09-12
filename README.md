# ReSukiSU-OnePlus-Legacy

为一加旧款 non-GKI / GKI 1.0 平台集成 ReSukiSU，目标产物为 **boot.img**。
首批面向各机型官方末代系统，ColorOS 优先、OxygenOS 次之。

**当前状态：源码与 Manual Hook 补丁检查通过；已登记 11 套原厂 boot 与内核配置；完整编译和真机验证尚未完成。没有已验证可刷写的发行版。**
完整固件编号、原厂 SHA-256 与来源见各机型 JSON；8 Pro OxygenOS 13.1.0.591 镜像尚待取得。

| 机型 | 独立分支 | 官方源码基线 | 内核 |
| --- | --- | --- | --- |
| 一加 8 | [oneplus-8](../../tree/oneplus-8) | Android 13 / OS 13.1 | 4.19.157 |
| 一加 8 Pro | [oneplus-8-pro](../../tree/oneplus-8-pro) | Android 13 / OS 13.1 | 4.19.157 |
| 一加 8T | [oneplus-8t](../../tree/oneplus-8t) | Android 14 / OS 14 | 4.19.157 |
| 一加 9R | [oneplus-9r](../../tree/oneplus-9r) | Android 14 / OS 14 | 4.19.157 |
| 一加 9 | [oneplus-9](../../tree/oneplus-9) | Android 14 / OS 14 | 5.4.254 |
| 一加 9 Pro | [oneplus-9-pro](../../tree/oneplus-9-pro) | Android 14 / OS 14 | 5.4.254 |

## 分支与系统布局

`main` 维护公共脚本和全部机型的源码锁定信息。机型分支通过根目录 `device.json` 选择自身配置，
构建工作流拒绝分支与机型不一致的请求。不同系统的成品分别存放，不能互换原厂 boot。

**9R：ColorOS 为 A-only，OxygenOS 为 A/B（维护者提供）。** 两者保持在 `oneplus-9r` 分支，
但使用各自的固件记录、原厂镜像和输出目录。A/B 槽位布局与 boot header 版本是不同概念。
其余已提取固件的 OTA 元数据标明 A/B；未取得的版本仍标记为 unverified。

## 已实现

- 六款机型独立配置；四个官方源码基线及 ReSukiSU 固定到完整 Git commit。
- 根据实际源码生成 execve、faccessat、stat/fstat、reboot 补丁；启用上游的 setuid、init rc、input 自动钩子。
- Linux 实验性编译工作流，产出 Image、kernel.config、源码／补丁／工具版本记录。
- 原厂 boot 校验和内核替换脚本；重新解包检查 ramdisk、DTB 等组件未变化。
- 六机型联网补丁检查，以及 9R 布局误用等本地测试。

## 使用

在 Actions 中选择 **Experimental kernel compile**，选择相应机型分支后运行。
构建默认读取对应系统原厂 boot 中提取的内核配置。当前使用 Ubuntu 22.04 的 Clang 14 验证编译链路；原厂 4.19 使用 Clang 10.0.7，5.4 使用 Clang 11.0.2，工具链与模块 CRC 兼容性仍须验证。
编译失败须修复源码／工具链依赖，不能据此宣称已支持对应固件。

本地 Linux 编译：

```sh
python3 scripts/build.py --device oneplus-9r --os coloros
# 若已获得匹配固件解出的完整内核配置，优先使用：
python3 scripts/build.py --device oneplus-9r --config /path/to/stock-kernel.config
```

成功编译后使用对应系统原厂 boot 打包（把占位项替换成实际值）：

```sh
python3 scripts/repack.py --device oneplus-9r --os coloros --layout a-only \
  --firmware EXACT_BUILD_ID --stock /path/to/stock-boot.img \
  --stock-sha256 ACTUAL_64_CHARACTER_SHA256
```

OxygenOS 9R 必须使用 `--os oxygenos --layout a/b` 及自己的原厂镜像。
输出为 `out/<机型>/<系统>-<完整版本>/boot.img`，旁附 `build.json` 和 `SHA256SUMS`。
打包工具仅使用锁定校验值的官方 Magisk 中的 magiskboot，不会安装 Magisk，也不会刷写手机。
新镜像大于原厂镜像时停止，需进一步核查实际分区容量。

## 完成适配前的必要工作

1. 补齐 8 Pro OxygenOS 13.1.0.591 原厂镜像；继续核对各地区末版版本。
2. 完成官方源码依赖、厂商功能配置、工具链和原厂模块 ABI 的比对及编译。
3. 使用各系统原厂 boot 打包；确认机型、地区、布局与固件记录一致。
4. 真机验证启动、解密、Wi-Fi、移动网络、相机、指纹、Root 授权及安全模式后，才标记验证通过。

当前设备配置中的空固件字段表示尚未取得该信息；不能用 OS 大版本推断任意补丁版本兼容。
项目不会自动发布或刷写未经验证的 boot。Root 构建会关闭 OPlus secure/root/mount/exec guard 冲突开关；保留 SELinux 配置。模块 release 字符串按原厂配置保留，真实源码提交另行记录，字符串相同并不等于模块 CRC 已匹配。

## 来源与许可

- [OnePlus SM8250 官方内核](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8250)
- [OnePlus SM8350 官方内核](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8350)
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU)
- [Manual Hook 文档](https://resukisu.org/guide/manual-integrate.html)
- [magiskboot](https://github.com/topjohnwu/Magisk)

本项目脚本与内核补丁使用 GPL-2.0-only。下载的上游代码及工具遵循各自许可证。
发布内核二进制时应同时提供对应源码版本、补丁、配置和构建说明。
