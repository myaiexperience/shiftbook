"""经验卡片：受限 YAML 子集 frontmatter 的解析。

刻意不支持嵌套结构——一旦允许嵌套，就得引入 PyYAML，
而这个项目的承诺是"零第三方依赖，NAS 上也能跑"。

支持：
    key: 值                    标量（字符串 / 整数 / 浮点 / true / false）
    key: [a, b, c]             行内列表
    key:                       空值，后面跟 "- 项" 行
      - a
      - b

解析不了就抛 CardError，**不猜**。手写的 Markdown 出问题时，
报错比"猜一个差不多"的值更有用。
"""

import datetime
import re

VALID_STATUS = ("draft", "active", "deprecated", "conflicting")
VALID_RISK = ("low", "medium", "high")
VALID_ADOPTION = ("suggestion", "preferred")
VALID_TYPE = ("fact", "preference")

# 正文小节的中英文别名。同一份卡片写中文或英文都能被检索到。
SECTION_ALIASES = {
    "symptom": ("场景", "症状", "context", "symptom"),
    "cause": ("根因", "原因", "cause", "root cause"),
    "fix": ("修正", "人工修正", "正确做法", "fix", "correction"),
    "not_when": ("不适用", "不适用条件", "什么时候不适用", "not when"),
}


class CardError(ValueError):
    """卡片格式错误。消息里带文件名，方便定位到具体那个 .md。"""


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _scalar(value):
    """把一段文本转成标量。空串返回 None（由调用方决定是否当成空列表）。"""
    value = value.strip()
    if not value:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        # 行内列表不处理引号内的逗号——文档里已写明，够用。
        return [_unquote(item) for item in inner.split(",") if item.strip()]
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return _unquote(value)


def parse(text, source="<text>"):
    """解析一张卡片，返回 (meta: dict, body: str)。"""
    if not text.lstrip("\ufeff").startswith("---"):
        raise CardError("%s: 缺少 frontmatter —— 文件必须以 --- 开头" % source)

    stripped = text.lstrip("\ufeff")
    end = stripped.find("\n---", 3)
    if end < 0:
        raise CardError("%s: frontmatter 没有闭合的 ---" % source)

    header = stripped[3:end]
    body = stripped[end + 4:]
    if body.startswith("\n"):
        body = body[1:]

    meta = {}
    current = None
    for lineno, raw in enumerate(header.splitlines(), start=4):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped == "-" or stripped.startswith("- "):
            # 列表项允许缩进（YAML 习惯），但键行不允许——那说明有人在写嵌套。
            if current is None:
                raise CardError("%s:%d: 列表项前面没有 key" % (source, lineno))
            if not isinstance(meta.get(current), list):
                raise CardError("%s:%d: key %r 已有非列表值，不能再接列表项"
                                % (source, lineno, current))
            item = stripped[2:].strip()
            if item:
                meta[current].append(_scalar(item))
            continue
        if line[:1].isspace():
            raise CardError("%s:%d: 缩进的键行（不支持嵌套）: %r"
                            % (source, lineno, line))
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if not match:
            raise CardError("%s:%d: 无法解析的行（不支持嵌套）: %r"
                            % (source, lineno, line))
        current = match.group(1).lower()
        tail = match.group(2)
        meta[current] = [] if not tail.strip() else _scalar(tail)
    return meta, body.strip()


def split_sections(body):
    """按 '## 标题' 切正文，返回 {小写标题: 内容}。"""
    out = {}
    current = None
    buf = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = line[3:].strip().lower()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(value)]


def _as_date(value):
    if isinstance(value, datetime.date):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class Card(object):
    """一张经验卡片。字段缺失时给安全默认值，但不隐藏格式错误。"""

    def __init__(self, meta, body, path=None):
        self.meta = meta
        self.body = body
        self.path = path
        self.sections = split_sections(body)

        self.id = str(meta.get("id") or "").strip()
        self.title = str(meta.get("title") or "").strip()
        if not self.id:
            raise CardError("%s: 缺少 id" % (path or "<card>"))
        if not self.title:
            raise CardError("%s: 缺少 title" % (path or "<card>"))

        self.status = str(meta.get("status") or "draft").strip().lower()
        if self.status not in VALID_STATUS:
            raise CardError("%s: status 必须是 %s（收到 %r）"
                            % (path or self.id, "|".join(VALID_STATUS), self.status))

        self.adoption = str(meta.get("adoption") or "suggestion").strip().lower()
        if self.adoption not in VALID_ADOPTION:
            raise CardError("%s: adoption 必须是 %s（收到 %r）"
                            % (path or self.id, "|".join(VALID_ADOPTION), self.adoption))

        self.risk = str(meta.get("risk") or "medium").strip().lower()
        if self.risk not in VALID_RISK:
            raise CardError("%s: risk 必须是 %s（收到 %r）"
                            % (path or self.id, "|".join(VALID_RISK), self.risk))

        self.type = str(meta.get("type") or "fact").strip().lower()
        if self.type not in VALID_TYPE:
            raise CardError("%s: type 必须是 %s（收到 %r）"
                            % (path or self.id, "|".join(VALID_TYPE), self.type))

        self.tags = _as_list(meta.get("tags"))
        self.triggers = _as_list(meta.get("triggers"))
        self.not_triggers = _as_list(meta.get("not_triggers"))
        self.scope = _as_list(meta.get("scope"))
        self.conflicts_with = _as_list(meta.get("conflicts_with"))

        self.created = _as_date(meta.get("created"))
        self.updated = _as_date(meta.get("updated")) or self.created
        self.review_after = _as_date(meta.get("review_after"))

        self.used = int(meta.get("used") or 0)
        self.helped = int(meta.get("helped") or 0)

    # ── 正文小节 ─────────────────────────────────────────────
    def section(self, key):
        """按别名取小节内容；取不到返回空串。

        '## 场景 / Context' 这种中英混排标题也算命中——手写卡片很自然会这么写。
        """
        for alias in SECTION_ALIASES.get(key, (key,)):
            text = self.sections.get(alias)
            if text:
                return text
            for header, value in self.sections.items():
                if value and header.startswith(alias):
                    return value
        return ""

    def one_line(self, limit=120):
        text = " ".join((self.section("fix") or self.section("symptom")).split())
        if len(text) > limit:
            text = text[:limit - 1].rstrip() + "…"
        return text

    def age_days(self, today=None):
        base = self.created
        if not base:
            return 0
        today = today or datetime.date.today()
        return max(0, (today - base).days)

    def is_stale(self, today=None):
        if not self.review_after:
            return False
        today = today or datetime.date.today()
        return self.review_after < today

    def __repr__(self):
        return "<Card %s %r>" % (self.id, self.title)


def load_card(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    meta, body = parse(text, source=str(path))
    return Card(meta, body, path=path)
