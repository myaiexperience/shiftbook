---
id: exp-seed-compose-config-check
title: 改 docker-compose 之后先跑一遍 config 校验，再 up
status: active
adoption: suggestion
type: fact
risk: low
scope: [any]
tags: [docker, compose, config]
triggers: [docker, compose, docker-compose, config, yaml, 校验, 语法, up, 启动失败]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2027-11-05
used: 0
helped: 0
---

## 场景 / Context
改完 docker-compose.yml 直接 `up -d`，容器起不来，日志里只有一句语焉不详的报错。
第一次排查往往从容器日志开始，而问题其实在文件里。

## 修正 / Fix
先 `docker compose config`（老版本 `docker-compose config`）——它只解析不启动，
YAML 缩进、变量未定义、挂载路径写错都会在这一步报出来。校验通过再 `up -d`。
这一步是几秒钟的事，能省掉一轮"起来→看日志→猜→改"。

## 不适用 / Not when
compose 文件里用了 `--env-file` 之外的自定义变量来源时，`config` 会因为变量为空
而报错——此时先补 env，不要把 `config` 的报错当成文件本身有问题。
