"""体检：找出会坏事的卡片。

只报告，不改文件——删卡一律由人确认后归档。
"自动清理"是这类工具最常见的自伤方式：它删掉的往往正是最该看的那张。
"""

import datetime

DRAFT_STALE_DAYS = 30
UNUSED_DAYS = 90
DUP_JACCARD = 0.8


def _jaccard(a, b):
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _keys(card):
    return [t.lower() for t in (card.tags + card.triggers)]


def check(cards, today=None, problems=None):
    """返回 findings 列表：每项是 dict(level, kind, id, message)。"""
    today = today or datetime.date.today()
    findings = []

    for path, message in (problems or []):
        findings.append({"level": "error", "kind": "parse", "id": path, "message": message})

    seen = {}
    for card in cards:
        if card.id in seen:
            findings.append({"level": "error", "kind": "duplicate-id", "id": card.id,
                             "message": "id 重复，另一份在 %s" % seen[card.id]})
        else:
            seen[card.id] = card.path

    for card in cards:
        if card.is_stale(today):
            findings.append({
                "level": "warn", "kind": "stale", "id": card.id,
                "message": "复核期限 %s 已过，内容可能过时" % card.review_after,
            })
        if (card.status == "draft" and card.created
                and (today - card.created).days > DRAFT_STALE_DAYS):
            findings.append({
                "level": "warn", "kind": "draft-rot", "id": card.id,
                "message": "草稿放了 %d 天没补完" % (today - card.created).days,
            })
        if card.status == "active" and card.used == 0 and card.age_days(today) >= UNUSED_DAYS:
            findings.append({
                "level": "info", "kind": "unused", "id": card.id,
                "message": "%d 天一次都没被检索命中过" % card.age_days(today),
            })
        for other_id in card.conflicts_with:
            findings.append({
                "level": "warn", "kind": "conflict", "id": card.id,
                "message": "声明与 %s 矛盾，两条都会进注入块，需要人裁决" % other_id,
            })

    for i, left in enumerate(cards):
        for right in cards[i + 1:]:
            score = _jaccard(_keys(left), _keys(right))
            if score >= DUP_JACCARD:
                findings.append({
                    "level": "info", "kind": "duplicate", "id": left.id,
                    "message": "与 %s 的标签/触发词重合 %.0f%%，可能该合并"
                               % (right.id, score * 100),
                })
    return findings


def report(findings):
    if not findings:
        return "体检通过：没有发现问题卡片。"
    order = {"error": 0, "warn": 1, "info": 2}
    marks = {"error": "✗", "warn": "!", "info": "·"}
    lines = ["体检结果：%d 条" % len(findings)]
    for item in sorted(findings, key=lambda f: (order.get(f["level"], 9), f["kind"])):
        lines.append("  %s [%s] %s — %s"
                     % (marks.get(item["level"], "?"), item["kind"],
                        item["id"], item["message"]))
    return "\n".join(lines)
