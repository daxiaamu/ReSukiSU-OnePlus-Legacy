# ReSukiSU-OnePlus-Legacy



为一加 8、8 Pro、8T、9R、9、9 Pro 集成 ReSukiSU，产物为 **boot.img**。项目面向 non-GKI / 早期 GKI 1.0 平台，使用各机型官方源码和对应末版系统的原厂 boot，不能套用通用 GKI 2.0 镜像。

**已完成 12 份实验版镜像。8 / 8 Pro / 8T / 9R 请使用 r2：已修复原厂模块签名证书缺失。9R ColorOS 已通过最终编译版临时启动复测；其他版本尚未真机验证。** ColorOS 为主，OxygenOS 为辅；下表列出本批次实际核对的完整版本，不表示同名系统的所有地区版本均通用。

| 机型 | 独立分支 | ColorOS | OxygenOS |
| --- | --- | --- | --- |
| 一加 8 | [oneplus-8](../../tree/oneplus-8) | IN2010_13.1.0.190(CN01) | IN2013_13.1.0.593(EX01) |
| 一加 8 Pro | [oneplus-8-pro](../../tree/oneplus-8-pro) | IN2020_13.1.0.190(CN01) | IN2023_13.1.0.591(EX01) |
| 一加 8T | [oneplus-8t](../../tree/oneplus-8t) | KB2000_14.0.0.602(CN01) | KB2001_14.0.0.1311(EX01) |
| 一加 9R | [oneplus-9r](../../tree/oneplus-9r) | LE2100_14.0.0.605(CN01) | LE2101_14.0.0.2401(EX01) |
| 一加 9 | [oneplus-9](../../tree/oneplus-9) | LE2110_14.0.0.1901(CN01) | LE2111_14.0.0.1902(EX01) |
| 一加 9 Pro | [oneplus-9-pro](../../tree/oneplus-9-pro) | LE2120_14.0.0.1901(CN01) | LE2121_14.0.0.1902(EX01) |

**9R 的 ColorOS 是 A-only，OxygenOS 是 A/B。** 两者在 `oneplus-9r` 分支内分别配置、分别封装；ColorOS 从 ZIP 直接提取 boot.img，OxygenOS 从 payload 提取。其余本批次固件均为 A/B。

## 成品与验证范围

每个成品目录包含 `boot.img`、`build.json`、`SHA256SUMS`；另有按机型和完整版本命名的 ZIP。镜像保存在本地 `out/`，不写入 Git 历史。校验值与构建记录见 [成品记录](docs/artifacts.json)。

- 9 / 9 Pro：13,797 个原厂内核导出接口名称与 CRC 全部匹配，保留原厂 CFI 配置，验证协议初始化回调的 CFI 签名。
- 8 / 8 Pro / 8T / 9R：核对各系统原厂 vendor、odm 的全部 41 个驱动模块，通过依赖 CRC、内核 release 和 PKCS#7 签名检查；保留强制签名校验。证书根因与修复见 [模块签名说明](docs/module-signing.md)，旧版校验值见 [撤回记录](docs/withdrawn-artifacts.json)。
- SM8250 保留两项公开源码内建触屏私有回调的结构差异。原厂驱动模块不引用这两项接口；其他原厂导出接口均匹配，没有缺失导出。原始差异报告保留在成品中，详见 [模块兼容性说明](docs/module-compatibility.md)。
- 每份镜像仅替换内核，重新解包核对原厂 ramdisk、DTB 等其他组件及 header，检查镜像大小；不安装 Magisk，不执行刷机。

上述检查不等于真机验证。开机、解密、触控、相机、指纹、无线网络、休眠及 Root 授权仍需要对应设备实测。公开源码与原厂内核可能存在未公开功能差异。

## 分支和构建

`main` 维护共用脚本与所有机型配置。机型分支的 `device.json` 选择构建目标；GitHub Actions 拒绝分支与机型不一致的请求。8 系列 / 9R 使用 4.19.157，9 / 9 Pro 使用 5.4.254。上游源码、ReSukiSU、补丁与工具链均记录版本或校验和。

在机型分支运行 **Experimental kernel compile** 工作流，选择 ColorOS 或 OxygenOS。本地 Linux 示例：

```sh
python3 scripts/build.py --device oneplus-9r --os coloros
```

同机型两套系统即使配置和导出 CRC 相同，也必须核对模块签名证书。SM8250 的 ColorOS、OxygenOS 证书不同，r2 分别编译，并使用各自的原厂 boot 封装。

原厂 ZIP 可从本地或只读共享读取，输出写入本项目：

```sh
python3 scripts/extract_stock.py --device oneplus-9r --os coloros \
  --rom /path/to/official.zip
# payload 格式另加 --dumper /path/to/payload_dumper
```

SM8250 在封装前还需提取对应 ROM 的 vendor、odm，按 [模块检查流程](docs/module-compatibility.md) 生成清单。完整导出表不匹配且没有原厂模块证据时，封装会拒绝继续。

```sh
python3 scripts/repack.py --device oneplus-9r --os coloros --layout a-only \
  --firmware 'LE2100_14.0.0.605(CN01)' \
  --stock .work/stock/oneplus-9r/coloros/boot.img \
  --stock-sha256 ACTUAL_64_CHARACTER_SHA256
```

OxygenOS 9R 使用 `--os oxygenos --layout a/b` 及其独立固件信息。原厂 SHA-256 和版本保存在 `devices/*.json`。完成全部机型封装后，运行 `python3 scripts/package_artifacts.py` 生成 ZIP、总校验表和本地成品索引。

## 来源与许可

- [OnePlus SM8250 官方内核](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8250)
- [OnePlus SM8350 官方内核](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8350)
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU)
- [magiskboot](https://github.com/topjohnwu/Magisk)
- [erofs-utils](https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git/)

项目脚本和内核补丁使用 GPL-2.0-only。上游代码及工具遵循各自许可证；分发内核二进制时应同时提供对应源码提交、补丁、配置和构建说明。
