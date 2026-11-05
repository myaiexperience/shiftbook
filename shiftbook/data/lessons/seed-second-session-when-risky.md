---
id: exp-seed-second-session-when-risky
title: 改可能断连的配置时，先另开一个会话保持连接
status: active
adoption: suggestion
type: fact
risk: high
scope: [any]
tags: [ssh, network, principle]
triggers: [ssh, 断连, 失联, 会话, session, 重启网络, network restart, 远程, 风险]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-11-05
used: 0
helped: 0
---

## 场景 / Context
执行 `systemctl restart networking` 或者改防火墙、改路由，当前 SSH 会话断了，
而重连也需要这条链路——于是一次可恢复的改动变成了要去现场。

## 修正 / Fix
动手前开第二个 SSH 会话，**什么都不干，就挂着**。
第一个会话做改动，如果它断了，第二个还在；如果第二个也断了，说明是链路问题，
而不是你的改动——这个信息本身就值一次现场往返。
配套一条：改动前先确认"从哪进来"能不能恢复（带外管理/另一条路径）。

## 不适用 / Not when
纯本地的文件改动、不影响网络栈的操作，不需要这条。
