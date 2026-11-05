---
id: exp-seed-env-not-in-image
title: .env 不要 COPY 进镜像，用 compose 的 env_file
status: active
adoption: preferred
type: fact
risk: high
scope: [any]
tags: [docker, security, config]
triggers: [.env, env, 环境变量, 镜像, dockerfile, copy, 密钥, token, 泄露]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2028-11-05
used: 0
helped: 0
---

## 场景 / Context
`COPY . .` 把 `.env` 一起打进镜像层。之后即使删掉文件，它仍然留在历史层里，
镜像推到任何地方都带着密钥。

## 修正 / Fix
1. `.dockerignore` 里加 `.env`、`*.key`、`data/`
2. 运行时用 `env_file:` 或 `environment:` 注入
3. 已经打进去的，别指望 `RUN rm` —— 重建镜像，并**轮换那批密钥**
判断标准：`docker history <image>` 里能看到的东西，别人也能看到。

## 不适用 / Not when
镜像只在本机、且从不推送、也从不共享时，风险低——但"只在本机"通常很快就不成立了。
