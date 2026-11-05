---
id: exp-seed-test-restore-not-just-backup
title: 备份只有在恢复过一次之后才算备份
status: active
adoption: preferred
type: fact
risk: high
scope: [any]
tags: [backup, principle]
triggers: [备份, backup, 恢复, restore, 还原, 验证, 快照, 数据丢失]
not_triggers: []
created: 2026-11-05
updated: 2026-11-05
review_after: 2028-11-05
used: 0
helped: 0
---

## 场景 / Context
备份任务天天跑、显示成功，真出事时发现备份是空的、或者恢复脚本指向的路径早就不存在。
"备份成功"通常只证明写入没报错，不证明能恢复。

## 修正 / Fix
把"恢复"当成备份的一部分：至少挑一个最近的备份，真的恢复到临时目录，
打开一个文件看看内容对不对。恢复验证的频率可以低（季度），但必须有。
同时检查恢复脚本本身——脚本里的路径会因为目录整理而失效，
而这类失效不会有人主动告诉你。

## 不适用 / Not when
不可再生的数据（照片、文档）要求更高：验证要覆盖"从备份到可读"的完整链路，
而不只是文件存在。
