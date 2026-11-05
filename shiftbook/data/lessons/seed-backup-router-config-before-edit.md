---
id: exp-seed-backup-router-config-before-edit
title: 改路由器/旁路由配置前，先备份 /etc/config 并确认能回滚
status: active
adoption: suggestion
type: fact
risk: high
scope: [any]
tags: [network, router, openwrt, backup]
triggers: [openwrt, 旁路由, 路由器, 网络, 配置, 修改, 备份, 回滚, 断网, 桥接]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-02-05
used: 0
helped: 0
---

## 场景 / Context
在旁路由上改网络配置（接口、桥接、防火墙），改错一步就连不上了，
而这时候你已经没有可用的管理通道——网络上不了网，SSH 也进不去。

## 修正 / Fix
改动前先 `cp -r /etc/config /root/config.bak.$(date +%s)`，并确认这个备份
**不在 tmpfs 上**（重启会丢）。如果设备支持，再导出一份配置到宿主机。
判断标准很简单：能不能说出"如果这一步改错，我用什么命令恢复"。
说不出来就别改。

## 不适用 / Not when
在虚拟机/容器里跑的路由，快照比文件备份更可靠——那种情况直接打快照，
备份文件的收益有限。
