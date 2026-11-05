---
id: exp-seed-dns-change-wait-ttl
title: 改 DNS 之后要等 TTL，别立刻判定"没生效"
status: active
adoption: suggestion
type: fact
risk: low
scope: [any]
tags: [dns, network]
triggers: [dns, 缓存, cache, ttl, 解析, 生效, 不生效, 刷新, 上游]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
改了 DNS 上游或解析记录，`nslookup` 还是旧结果，于是判断"配置没生效"，
反复重启服务。实际上可能是客户端缓存、本地缓存、上游缓存三层都还没过期。

## 修正 / Fix
排查顺序：客户端缓存 → 本地 DNS 服务缓存 → 上游 TTL。
`dig @<server> <name> +short` 直接问指定服务器，绕开客户端缓存；
再 `dig` 一次看 TTL 还剩多少。确认服务端已经是新值时，
剩下的就是等——把等待时间写进记录，别反复重启。

## 不适用 / Not when
TTL 设得很长（比如 86400）且需要快速切换时，正确做法是**提前调小 TTL**，
切换完再调回去，而不是切完干等。
