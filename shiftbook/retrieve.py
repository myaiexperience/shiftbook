"""检索：BM25 + 字段权重 + 置信度/新鲜度衰减 + 设备硬过滤。

为什么不用 ripgrep：
  * rg 没有排序，给不出"哪条更相关"
  * rg 没有字段权重，"title 里命中"和"正文里命中"一样重
  * rg 对中文不切词，整句当一行匹配

为什么不用向量：
  语料是几百张卡片，BM25 足够；向量要模型、要常驻、要防幻觉。
  留成可插拔后端（见 DECISIONS.md）。
"""

import datetime
import math
import re

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9_+#.\-]*")

K1 = 1.2
B = 0.75

# (字段名, 权重)。field=None 表示正文全文。
FIELDS = (
    ("title", 3.0),
    ("triggers", 3.0),
    ("tags", 2.0),
    ("symptom", 2.0),
    ("cause", 1.5),
    ("fix", 1.0),
)

# 不同领域的知识老化速度不同。改的是半衰期（天）。
TAG_HALF_LIFE = {
    "network": 60, "network-config": 60, "topology": 60, "ipvlan": 60,
    "macvlan": 60, "dns": 90, "model": 90, "version": 90, "package": 90,
    "docker": 180, "compose": 180, "config": 180, "backup": 365,
    "principle": 720, "any": 365,
}
DEFAULT_HALF_LIFE = 180


def tokenize(text):
    """英文按词，中文按二元组（bigram）。不依赖 jieba。"""
    if not text:
        return []
    text = text.lower()
    tokens = [m.group(0) for m in WORD_RE.finditer(text)]
    for match in CJK_RE.finditer(text):
        run = match.group(0)
        if len(run) == 1:
            tokens.append(run)
            continue
        for i in range(len(run) - 1):
            tokens.append(run[i:i + 2])
    return tokens


def half_life(card):
    for tag in card.tags:
        key = tag.strip().lower()
        if key in TAG_HALF_LIFE:
            return TAG_HALF_LIFE[key]
    return DEFAULT_HALF_LIFE


def freshness(card, today=None):
    """0.5 ^ (age / half_life)。越老越轻，但不归零。"""
    today = today or datetime.date.today()
    age = card.age_days(today)
    return 0.5 ** (float(age) / half_life(card))


def confidence(card):
    """adoption 基础分 × 战绩。

    trust = (helped + 1) / (used + 2)   —— 拉普拉斯平滑：
        没用过 = 0.5，3 次全中 = 0.8，3 次全错 = 0.2
    F_conf = adoption_base × (0.5 + trust)
        suggestion & 没用过 = 0.60 ｜ preferred & 全中 = 0.90
    故意让"没用过"不是 1.0：新卡不该比验证过的卡更响。
    """
    trust = float(card.helped + 1) / float(card.used + 2)
    base = 1.0 if card.adoption == "preferred" else 0.6
    return base * (0.5 + trust)


def scope_factor(card, device):
    """设备不匹配直接排除（返回 0），不靠扣分。"""
    if not device:
        return 1.0 if not card.scope else 0.85
    scopes = [s.strip().lower() for s in card.scope]
    if not scopes or "any" in scopes or "*" in scopes:
        return 0.85
    return 1.0 if device.strip().lower() in scopes else 0.0


class Index(object):
    """内存倒排索引。几百张卡片时全量构建 < 10ms，不值得做增量。"""

    def __init__(self, cards):
        self.cards = [c for c in cards if c.status in ("active", "conflicting", "draft")]
        self.docs = []
        self.df = {}
        self.avgdl = 1.0
        for card in self.cards:
            tf = {}
            dl = 0.0
            for field, weight in FIELDS:
                text = card.title if field == "title" else (
                    " ".join(card.triggers) if field == "triggers" else (
                        " ".join(card.tags) if field == "tags" else card.section(field)))
                for token in tokenize(text):
                    tf[token] = tf.get(token, 0.0) + weight
                    dl += weight
            self.docs.append((tf, dl))
            for token in tf:
                self.df[token] = self.df.get(token, 0) + 1
        if self.docs:
            self.avgdl = sum(dl for _, dl in self.docs) / float(len(self.docs))
        self.n = len(self.docs)

    def idf(self, token):
        df = self.df.get(token, 0)
        return math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query, device=None, today=None, limit=None):
        all_terms = sorted(set(tokenize(query)))
        # 只统计**语料里真的存在**的词。
        # 中文二元组会切出一堆"的上 / 让它 / 它指"这种语料里根本不存在的碎片，
        # 把它们算进覆盖率分母，会把真正命中的卡片压到阈值以下。
        terms = [t for t in all_terms if self.df.get(t)]
        if not terms or not self.docs:
            return []
        # 覆盖率用 idf 加权，且**与语料规模无关**：
        # 绝对分数会随文档数变化（1 张卡时 BM25 永远到不了 1.0），
        # 用它当"强命中"阈值会让小库永远只能出弱提示。
        idf_sum = sum(self.idf(t) for t in terms) or 1.0
        results = []
        for card, (tf, dl) in zip(self.cards, self.docs):
            gate = scope_factor(card, device)
            if gate <= 0:
                continue
            score = 0.0
            matched = []
            covered = 0.0
            for term in terms:
                f = tf.get(term)
                if not f:
                    continue
                matched.append(term)
                covered += self.idf(term)
                denom = f + K1 * (1.0 - B + B * dl / self.avgdl)
                score += self.idf(term) * (f * (K1 + 1.0)) / denom
            if not matched:
                continue
            # 负向词：命中就砍分，防止 "重启容器" 命中 "重装容器"。
            # 这里必须对**原始查询词**判断：负向词本身通常不在语料里，
            # 用过滤后的 terms 去比，等于永远不触发。
            for negative in card.not_triggers:
                if any(t in all_terms for t in tokenize(negative)):
                    score *= 0.3
            score *= freshness(card, today) * confidence(card) * gate
            if card.status == "deprecated":
                continue
            results.append(Hit(card, score, matched, covered / idf_sum))
        results.sort(key=lambda h: h.score, reverse=True)
        return results[:limit] if limit else results


class Hit(object):
    def __init__(self, card, score, matched, coverage=0.0):
        self.card = card
        self.score = score
        self.matched = matched
        self.coverage = coverage

    def __repr__(self):
        return "<Hit %.3f cov=%.2f %s>" % (self.score, self.coverage, self.card.id)


def tier(hit):
    """按查询词覆盖率分档——这个量不随语料规模漂移。"""
    if hit.card.status == "conflicting":
        return "conflict"
    if hit.coverage >= 0.5:
        return "strong"
    if hit.coverage >= 0.2:
        return "weak"
    return "drop"


def select(results, max_cards=3):
    """只让排名第一的卡出摘要，其余降成一行。"""
    if not results:
        return []
    out = []
    strong_left = 1
    for rank, hit in enumerate(results):
        level = tier(hit)
        if level == "drop":
            continue
        if level == "conflict":
            out.append(hit)
            continue
        if level == "strong" and strong_left > 0 and rank == 0:
            out.append(hit)
            strong_left -= 1
            continue
        out.append(hit)
        if len(out) >= max_cards:
            break
    return out[:max_cards]
