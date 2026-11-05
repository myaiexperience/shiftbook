"""生成草稿卡片文本。CLI 落盘、魔搭演示在内存里用，共用这一份。

刻意不在这里写盘：谁调用谁负责持久化，演示才能做到"不落盘、不收集输入"。
"""

import datetime
import hashlib


def _slug(text, keep=6):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:keep]


def build_card_text(text, device=None, tags=None, risk="medium", today=None):
    """返回 (card_id, 卡片全文)。"""
    today = today or datetime.date.today()
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("要记的内容不能为空")

    card_id = "exp-%s-%s" % (today.strftime("%Y%m%d"), _slug(text))
    title = text if len(text) <= 40 else text[:39] + "…"
    review = (today + datetime.timedelta(days=90)).isoformat()
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    lines = [
        "---",
        "id: %s" % card_id,
        "title: %s" % title,
        "status: draft",
        "adoption: suggestion",
        "type: fact",
        "risk: %s" % (risk or "medium"),
        "scope: [%s]" % (device or "any"),
        "tags: [%s]" % ", ".join(tag_list),
        "triggers: []",
        "created: %s" % today.isoformat(),
        "updated: %s" % today.isoformat(),
        "review_after: %s" % review,
        "used: 0",
        "helped: 0",
        "---",
        "",
        "## 场景",
        text,
        "",
        "## 修正",
        "（待补：当时正确的做法是什么）",
        "",
        "## 不适用",
        "（待补：什么情况下这条不该套用）",
        "",
    ]
    return card_id, "\n".join(lines)
