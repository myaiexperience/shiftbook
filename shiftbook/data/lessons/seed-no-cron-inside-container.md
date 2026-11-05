---
id: exp-seed-no-cron-inside-container
title: 容器里的 cron 不可靠，定时任务放宿主或独立 sidecar
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [docker, cron, scheduling]
triggers: [cron, 定时, 计划任务, 容器, docker, 不执行, 时区, 重启丢失]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
在容器里装了 cron，任务一段时间后不跑了。原因通常是：容器重启后 cron 没起来、
镜像里没有 init、时区是 UTC、或者容器被回收重建后改动全丢。

## 修正 / Fix
定时任务放三个地方之一：
1. 宿主机的 cron / systemd timer（最稳，日志好查）
2. 独立 sidecar 容器（`ofelia` 之类），与业务容器解耦
3. 编排层自带的能力（如果有）
容器内 cron 只在"这个镜像本来就是为它设计的"时才用。

## 不适用 / Not when
镜像的 entrypoint 明确负责拉起 cron 且容器不重建（固定容器）时，容器内 cron 可以接受。
