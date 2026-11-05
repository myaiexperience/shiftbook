---
id: exp-seed-rename-needs-network-recreate
title: macvlan/ipvlan 下改容器名，要连网络一起重建
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [docker, network, macvlan, config]
triggers: [macvlan, ipvlan, 容器名, 改名, rename, 网络, 重建, 连不上]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
把容器从 `openwrt` 改名成 `openwrt-main`，容器起来了，但网络不通。
原因是 macvlan/ipvlan 网络在创建时记录了接入容器的名字，改名之后
网络那一侧还对着旧名字。

## 修正 / Fix
改名的成本 = 删容器 + 删网络 + 重建网络 + 重建容器。
先导出容器配置，再 `docker network rm`，然后按新名字建网络和容器。
不要在容器已经起来之后再补网络——顺序错了会遇到"网络存在但接不上"。

## 不适用 / Not when
bridge 网络下改名不影响连接，只需重新 `docker network connect` 即可。
