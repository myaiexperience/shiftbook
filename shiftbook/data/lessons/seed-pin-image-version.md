---
id: exp-seed-pin-image-version
title: 镜像别用 latest，锁版本，升级单独做一次
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [docker, version, upgrade]
triggers: [latest, 镜像, image, tag, 版本, 固定, 升级, 回滚, 不兼容]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
`image: xxx:latest`，某天容器重启就拉到了新版本，行为变了、配置格式变了，
而你手上没有任何"之前是哪个版本"的信息，回滚都无从下手。

## 修正 / Fix
1. 所有镜像固定到具体版本号（或 digest）
2. 升级时改版本号 → 重建 → 验证 → 记录
3. 保留上一个可用版本号在注释里，回滚就是改回去
"锁版本"的代价是手动升级，收益是出事时你知道该退回哪里。

## 不适用 / Not when
一次性工具容器（跑完即弃）用 latest 无所谓，它不承载状态。
