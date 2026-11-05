---
id: exp-seed-port-conflict-find-owner
title: 端口被占用，先用 ss 找到占用者，再决定改端口还是停服务
status: active
adoption: suggestion
type: fact
risk: low
scope: [any]
tags: [network, docker, port]
triggers: [端口, port, 占用, 冲突, bind, address already in use, ss, netstat, 启动失败]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-11-05
used: 0
helped: 0
---

## 场景 / Context
容器或服务启动报 `address already in use`。常见处理是"换个端口试试"，
但如果占用者是另一个还在跑的服务，换端口只是把冲突推后。

## 修正 / Fix
`ss -lntp | grep :<port>`（或 `lsof -i :<port>`）先看是谁占的。
如果是自己忘关的旧进程 → 停掉它，保留原端口（配置不用改，少一次改动）。
如果是另一个正常服务 → 才改端口，并同步改反代/防火墙/文档三处。
**改端口是三处改动，停进程是一处改动**，优先选改动少的。

## 不适用 / Not when
容器使用 host 网络模式时，`ss` 看到的是宿主进程，
占用者可能就是容器本身——先 `docker ps` 再判断。
