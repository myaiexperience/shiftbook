---
id: exp-seed-disk-full-check-logs-first
title: 磁盘满了先查 docker 日志与 overlay2，别急着删用户数据
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [storage, docker, disk]
triggers: [磁盘, disk, 空间, full, 满了, 日志, log, overlay2, docker, 清理]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
`No space left on device`。第一反应是删东西，但删用户数据不可逆，
而磁盘占用的常见大头往往是可再生的：容器日志、悬空镜像、overlay2 层。

## 修正 / Fix
按这个顺序查：
1. `docker system df -v` —— 镜像/容器/卷/构建缓存各占多少
2. `du -sh /var/lib/docker/*` —— 找出到底是哪一块
3. 容器日志：`docker inspect --format='{{.LogPath}}' <name>` 看单个日志多大
先清这三样，再考虑动数据。清完用 `df -h` 确认，别凭感觉。

## 不适用 / Not when
已经触发只读挂载（ext4 的 `errors=remount-ro`）时，先解决挂载状态，
否则清出来的空间写不进去，看起来像"清了没用"。
