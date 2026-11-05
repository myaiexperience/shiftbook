"""卡片仓库：从一个或多个目录读取 .md 卡片。

读不动一张卡片，不能让整次检索挂掉——手写的 Markdown 迟早会有一张写错。
所以：坏卡片收集到 problems 里，好卡片照常返回。
"""

import os

from .card import CardError, load_card

SKIP_DIRS = ("__pycache__", ".git", "_archive", ".shiftbook")


def card_paths(*roots):
    """递归列出所有卡片路径，按路径排序保证结果稳定。"""
    found = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames
                                 if d not in SKIP_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                if not name.endswith(".md") or name.startswith("_"):
                    continue
                # README 之类不是卡片，但它也会以 --- 开头（模型卡）。
                if name.lower() in ("readme.md", "readme.en.md"):
                    continue
                found.append(os.path.join(dirpath, name))
    return found


def load_cards(*roots):
    """返回 (cards, problems)。problems 是 [(path, 错误信息)]。"""
    cards = []
    problems = []
    for path in card_paths(*roots):
        try:
            cards.append(load_card(path))
        except CardError as exc:
            problems.append((path, str(exc)))
        except (OSError, UnicodeDecodeError) as exc:
            problems.append((path, "读取失败: %s" % exc))
    return cards, problems


def find_duplicate_ids(cards):
    """同一份仓库里 id 重复，检索去重时会静默吞掉一张。必须报出来。"""
    seen = {}
    dupes = []
    for card in cards:
        if card.id in seen:
            dupes.append((card.id, seen[card.id], card.path))
        else:
            seen[card.id] = card.path
    return dupes
