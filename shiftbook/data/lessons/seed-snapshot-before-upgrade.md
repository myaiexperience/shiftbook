---
id: exp-seed-snapshot-before-upgrade
title: 升级前先打快照，而且升级和改配置分两次做
status: active
adoption: suggestion
type: fact
risk: high
scope: [any]
tags: [upgrade, backup, version]
triggers: [升级, upgrade, 更新, update, 快照, snapshot, 固件, 系统, 回滚]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
一次操作里既升级了系统又改了配置，出问题后无法判断是哪一边导致的，
回滚时也不知道该回滚什么。这是排查成本最高的一种组合。

## 修正 / Fix
两条规矩：
1. **升级前打快照**，快照命名带日期和当前版本号，方便事后对号。
2. **一次只动一个变量**：升级就只升级，配置改动放到下一轮。
出问题时，"上次能跑"和"这次不能跑"之间只应该差一件事。

## 不适用 / Not when
安全补丁、紧急修复可以合并做，但要在记录里写清"这次合并了哪两件事"，
否则下次排查会重新踩一遍。
