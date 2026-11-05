"""命令行入口。零第三方依赖，只用 argparse。

命令动词给两套：英文（note/find/doctor）和中文（记/找/体检）。
中文键入更快，英文对开源用户友好，两个都留。
"""

import argparse
import datetime
import json
import os
import shutil
import sys

from . import __version__, doctor as doctor_mod, inject, retrieve, store
from .card import Card, CardError
from .notecard import build_card_text

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_DIR = os.path.join(HERE, "data", "lessons")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOHIT = 3


def ensure_utf8_stdio():
    """Windows 控制台默认 cp936，中文输出会炸。这个坑踩过。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def root_dir(args):
    return os.path.abspath(args.root or os.environ.get("SHIFTBOOK_HOME") or os.getcwd())


def card_dirs(root):
    return [os.path.join(root, "cards"), os.path.join(root, "lessons")]



# ── init ─────────────────────────────────────────────────────

def cmd_init(args):
    root = root_dir(args)
    cards_dir = os.path.join(root, "cards")
    data_dir = os.path.join(root, "data")
    lessons_dir = os.path.join(root, "lessons")
    for path in (cards_dir, data_dir, lessons_dir):
        os.makedirs(path, exist_ok=True)

    copied = 0
    if os.path.isdir(SEED_DIR):
        for name in sorted(os.listdir(SEED_DIR)):
            if not name.endswith(".md"):
                continue
            target = os.path.join(lessons_dir, name)
            if os.path.exists(target):
                continue
            shutil.copyfile(os.path.join(SEED_DIR, name), target)
            copied += 1

    print("值班本已就位：%s" % root)
    print("  cards/    你自己的经验（想怎么改怎么改）")
    print("  lessons/  种子经验 %d 条（%s）" % (copied, "本次新装" if copied else "已存在，未覆盖"))
    print("  data/     原始记录（inbox.jsonl）")
    print("")
    print("下一步：python -m shiftbook 记 \"改 AdGuard 配置前先停容器\"")
    return EXIT_OK


# ── note ─────────────────────────────────────────────────────

def cmd_note(args):
    root = root_dir(args)
    text = " ".join((args.text or "").split())
    if not text:
        print("要记的内容不能为空", file=sys.stderr)
        return EXIT_ERROR

    data_dir = os.path.join(root, "data")
    cards_dir = os.path.join(root, "cards")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cards_dir, exist_ok=True)

    now = datetime.datetime.now()
    record = {
        "ts": now.isoformat(timespec="seconds"),
        "text": text,
        "device": args.device or "",
        "tags": args.tags or "",
    }
    with open(os.path.join(data_dir, "inbox.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    card_id, card_text = build_card_text(text, device=args.device,
                                         tags=args.tags, risk=args.risk)
    path = os.path.join(cards_dir, card_id + ".md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(card_text)

    print("已记录：%s" % path)
    print("  triggers 还是空的——补上几个触发词，检索才会稳。")
    return EXIT_OK


# ── find ─────────────────────────────────────────────────────

def cmd_find(args):
    root = root_dir(args)
    cards, problems = store.load_cards(*card_dirs(root))
    index = retrieve.Index(cards)
    results = index.search(args.query, device=args.device, limit=20)
    hits = retrieve.select(results, max_cards=args.max_cards)

    if args.json:
        payload = {
            "query": args.query,
            "device": args.device,
            "cards_loaded": len(cards),
            "problems": [{"path": p, "message": m} for p, m in problems],
            "hits": [{"id": h.card.id, "title": h.card.title,
                      "score": round(h.score, 4),
                      "status": h.card.status, "matched": h.matched}
                     for h in hits],
            "block": inject.render(hits, budget=args.budget),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK if hits else EXIT_NOHIT

    for path, message in problems:
        print("[跳过] %s" % message, file=sys.stderr)
    if not hits:
        print("没有命中任何经验（共 %d 张卡）。" % len(cards))
        return EXIT_NOHIT
    print(inject.explain(hits))
    print("")
    print(inject.render(hits, budget=args.budget))
    return EXIT_OK


# ── doctor ───────────────────────────────────────────────────

def cmd_doctor(args):
    root = root_dir(args)
    cards, problems = store.load_cards(*card_dirs(root))
    findings = doctor_mod.check(cards, problems=problems)
    if args.json:
        print(json.dumps({"cards": len(cards), "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        print("共 %d 张卡片" % len(cards))
        print(doctor_mod.report(findings))
    errors = [f for f in findings if f["level"] == "error"]
    return EXIT_ERROR if errors else EXIT_OK


# ── bench ────────────────────────────────────────────────────

def cmd_bench(args):
    root = root_dir(args)
    path = args.cases or os.path.join(root, "benchmarks", "cases.jsonl")
    if not os.path.exists(path):
        print("找不到基准文件：%s" % path, file=sys.stderr)
        return EXIT_ERROR
    cases = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))

    cards, _ = store.load_cards(*card_dirs(root))
    index = retrieve.Index(cards)
    top1 = 0
    mrr = 0.0
    for case in cases:
        results = index.search(case["query"], device=case.get("device"), limit=10)
        ids = [h.card.id for h in results]
        want = case.get("expect_top") or []
        if ids and want and ids[0] in want:
            top1 += 1
        for rank, cid in enumerate(ids[:10], start=1):
            if cid in want:
                mrr += 1.0 / rank
                break
    n = len(cases) or 1
    print("基准：%d 例 ｜ Top-1 命中 %.0f%% ｜ MRR %.3f ｜ 卡片 %d 张"
          % (len(cases), 100.0 * top1 / n, mrr / n, len(cards)))
    return EXIT_OK


# ── demo ─────────────────────────────────────────────────────

DEMO_TASK = "改 AdGuardHome 的上游 DNS，让它指到新的旁路由"
DEMO_DEVICE = "nas"


def cmd_demo(args):
    """把"一次纠正 → 下次规划前被带出来"演一遍，用的是真引擎。"""
    root = root_dir(args)
    cards, problems = store.load_cards(*card_dirs(root))
    print("=" * 62)
    print("值班本演示 —— 一次人工介入，如何变成下一次的护栏")
    print("=" * 62)
    print("")
    print("① 现在有 %d 张卡片（其中 %d 张来自种子库）"
          % (len(cards), len([c for c in cards if c.path and "lessons" in c.path])))
    print("")
    print("② 任务：%s" % DEMO_TASK)
    print("   设备：%s" % DEMO_DEVICE)
    print("")
    index = retrieve.Index(cards)
    before = retrieve.select(index.search(DEMO_TASK, device=DEMO_DEVICE), max_cards=3)
    print("③ 规划前检索（注入预算 %d 字符）：" % args.budget)
    print("")
    block = inject.render(before, budget=args.budget)
    print(block if block else "（空——库里还没有相关经验）")
    print("")
    print("④ 上面每一条都带 id。方案里回引 id，才能统计「这条经验有没有用」。")
    print("   本例命中 %d 条；没有命中的任务，注入块就是空的，不会硬凑。" % len(before))
    if problems:
        print("")
        print("⑤ 顺带：%d 张卡片格式有问题，已跳过（体检会点名）" % len(problems))
    return EXIT_OK


def cmd_version(args):
    print("值班本 shiftbook %s" % __version__)
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(
        prog="shiftbook",
        description="值班本 —— 让你的 AI 工程师更懂你。",
        epilog="命令动词中英双写：note/记、find/找、doctor/体检。",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--root", help="工作目录（默认当前目录，或 SHIFTBOOK_HOME）")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", aliases=["初始化"], help="建立目录并铺种子经验")
    p_init.set_defaults(func=cmd_init)

    p_note = sub.add_parser("note", aliases=["记"], help="记一条（零摩擦，不填表）")
    p_note.add_argument("text", help="一句话：哪里不对、正确的做法是什么")
    p_note.add_argument("--device", help="设备名，如 nas / pc / ubuntu")
    p_note.add_argument("--tags", help="逗号分隔的标签")
    p_note.add_argument("--risk", choices=("low", "medium", "high"))
    p_note.set_defaults(func=cmd_note)

    p_find = sub.add_parser("find", aliases=["找"], help="规划前检索")
    p_find.add_argument("query", help="任务描述")
    p_find.add_argument("--device", help="设备名，不匹配的卡片会被硬过滤")
    p_find.add_argument("--budget", type=int, default=1200, help="注入块字符预算")
    p_find.add_argument("--max-cards", type=int, default=3)
    p_find.add_argument("--json", action="store_true")
    p_find.set_defaults(func=cmd_find)

    p_doc = sub.add_parser("doctor", aliases=["体检"], help="查过时/重复/矛盾卡片")
    p_doc.add_argument("--json", action="store_true")
    p_doc.set_defaults(func=cmd_doctor)

    p_bench = sub.add_parser("bench", aliases=["基准"], help="跑检索基准")
    p_bench.add_argument("--cases", help="cases.jsonl 路径")
    p_bench.set_defaults(func=cmd_bench)

    p_demo = sub.add_parser("demo", aliases=["演示"], help="跑一遍完整案例")
    p_demo.add_argument("--budget", type=int, default=1200)
    p_demo.set_defaults(func=cmd_demo)

    p_ver = sub.add_parser("version", aliases=["版本"], help="版本号")
    p_ver.set_defaults(func=cmd_version)
    return parser


def main(argv=None):
    ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_OK
    try:
        return args.func(args)
    except CardError as exc:
        print("卡片格式错误：%s" % exc, file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
