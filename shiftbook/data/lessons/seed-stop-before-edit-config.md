---
id: exp-seed-stop-before-edit-config
title: 改服务自己的配置文件之前，先停它的容器
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [docker, config]
triggers: [adguard, adguardhome, yaml, 配置, 修改, 回写, 覆盖, 重启, 不生效]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
在宿主机上改 AdGuardHome / 某些自管配置的服务，改完重启容器，改动没了。
这类服务在退出或启动时会把内存里的配置**写回**文件，你改的那份被覆盖。
表现为"改了不生效"或"重启后变回去"，很容易误判成权限问题。

## 修正 / Fix
顺序固定为：`docker stop <name>` → 改文件 → `docker start <name>`。
改完先看文件里的关键行还在不在，再启动；启动后再看一次有没有被改回去。
判断这类服务的方法：配置文件旁边有 `.bak`、或者日志里出现 "saving configuration"。

## 不适用 / Not when
配置文件是只读挂载（`:ro`）或由环境变量生成的服务，停容器没有意义——
那类服务的正确改法是改 compose 或 env，不是改文件。
