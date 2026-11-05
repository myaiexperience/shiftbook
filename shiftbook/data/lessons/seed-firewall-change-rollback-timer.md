---
id: exp-seed-firewall-change-rollback-timer
title: 远程改防火墙前，先挂一个几分钟后自动回滚的任务
status: active
adoption: preferred
type: fact
risk: high
scope: [any]
tags: [network, firewall, ssh]
triggers: [防火墙, firewall, iptables, nftables, 规则, 远程, ssh, 锁死, 失联, 回滚]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-11-05
used: 0
helped: 0
---

## 场景 / Context
通过 SSH 改防火墙规则，新规则把自己所在的连接也挡了。命令一执行，会话立刻断，
而你已经进不去了。这类事故的代价通常是"跑去物理接触设备"。

## 修正 / Fix
改动前先挂一个延时回滚：
`( sleep 300; <恢复命令> ) &`，确认（`jobs`）它真的在跑，然后再改规则。
改完验证通过，再把那个后台任务 kill 掉。
核心不是这条命令，而是那个习惯：**任何可能导致失联的操作，都先留一条后路。**

## 不适用 / Not when
本地控制台/带外管理（IPMI、串口）可用时，失联的风险下降，
但仍建议先备份规则再改。
