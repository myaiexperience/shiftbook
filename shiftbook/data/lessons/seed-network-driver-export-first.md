---
id: exp-seed-network-driver-export-first
title: 改容器网络驱动（macvlan/ipvlan/bridge）前，先导出容器配置
status: active
adoption: suggestion
type: fact
risk: high
scope: [any]
tags: [docker, network, macvlan, ipvlan, topology]
triggers: [macvlan, ipvlan, bridge, 网络, 驱动, 切换, 容器重建, 断网, dhcp, 网关]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-02-05
used: 0
helped: 0
---

## 场景 / Context
把容器的网络从 macvlan 切到 ipvlan（或反过来），因为容器的网络配置是创建时
写死的，改驱动基本等于**删容器重建**。重建过程里只要有一处没备份，
就只能从记忆里恢复配置——而记忆通常不完整。

## 修正 / Fix
切换前必须做三件事：
1. `docker inspect <name> > /root/<name>.inspect.json`（完整配置快照）
2. 备份映射的配置文件目录
3. 记下 IP、网关、MAC、容器名——容器名会进网络配置，改名要重建网络
切完立刻验证两件事：容器能不能拿到地址、宿主机能不能连到它。验证不过就回退，
不要在"半通"的状态上继续加改动。

## 不适用 / Not when
用 compose 管理、且 compose 文件完整描述了网络与挂载时，重建是幂等的，
导出配置的收益下降——但备份数据卷仍然要做。
