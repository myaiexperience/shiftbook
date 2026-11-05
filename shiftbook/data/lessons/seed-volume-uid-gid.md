---
id: exp-seed-volume-uid-gid
title: 卷权限不对，先确认容器内 uid/gid，再 chown
status: active
adoption: suggestion
type: fact
risk: medium
scope: [any]
tags: [docker, permission, volume]
triggers: [权限, permission, denied, chown, uid, gid, 卷, volume, 挂载, 读写]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-05-05
used: 0
helped: 0
---

## 场景 / Context
容器报 `Permission denied`，在宿主机上 `chown -R 1000:1000` 之后有的能读、
有的还是不行。原因是不同镜像里跑服务的用户 uid 不一样，1000 只是猜的。

## 修正 / Fix
先查容器里实际是谁在跑：`docker exec <name> id`（或看镜像的 USER）。
拿到 uid/gid 再在宿主机上 chown，精确到需要写的那几个目录，
不要对整个数据盘 `chown -R`——那会顺带改掉别的服务的属主。

## 不适用 / Not when
使用 NFS/CIFS 挂载时，chown 可能无效（由服务端映射 uid），
此时改挂载参数（`uid=`/`gid=`）而不是在本地 chown。
