"""核心逻辑测试。零第三方依赖，用标准库 unittest。

跑法：python -m unittest discover -s tests -v
"""

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 有些受限环境（沙箱 / 只读挂载）写不了系统临时目录，
# 有些环境里 mkdtemp 建出来的目录又写不进去（受限令牌 + 0700 权限）。
# 统一改用 os.makedirs 在仓库内建临时目录，跑完自己收拾。
TMP_ROOT = os.path.join(ROOT, ".tmp-test")
os.makedirs(TMP_ROOT, exist_ok=True)


def new_tmp():
    import uuid
    path = os.path.join(TMP_ROOT, "t-" + uuid.uuid4().hex[:10])
    os.makedirs(path, exist_ok=True)
    return path

from shiftbook import card as card_mod          # noqa: E402
from shiftbook import doctor as doctor_mod      # noqa: E402
from shiftbook import inject, retrieve, store   # noqa: E402
from shiftbook.card import Card, CardError      # noqa: E402
from shiftbook.cli import main                  # noqa: E402

SEEDS = os.path.join(ROOT, "shiftbook", "data", "lessons")


def make_card(text, path=None):
    meta, body = card_mod.parse(text)
    return Card(meta, body, path=path)


MINIMAL = """---
id: exp-test-a
title: 改配置前先停容器
status: active
scope: [nas]
tags: [docker, config]
triggers: [adguard, 上游, upstream, 配置]
used: 0
helped: 0
---

## 场景
改 AdGuard 配置后重启，改动被写回覆盖。

## 修正
先 docker stop 再改，改完再 start。
"""


class TestFrontmatter(unittest.TestCase):
    def test_scalar_and_inline_list(self):
        meta, body = card_mod.parse(MINIMAL)
        self.assertEqual(meta["id"], "exp-test-a")
        self.assertEqual(meta["tags"], ["docker", "config"])
        self.assertIn("docker stop", body)

    def test_block_list(self):
        text = "---\nid: x\ntitle: t\ntriggers:\n  - a\n  - b\n---\n\nbody\n"
        meta, _ = card_mod.parse(text)
        self.assertEqual(meta["triggers"], ["a", "b"])

    def test_missing_fence_is_error(self):
        with self.assertRaises(CardError):
            card_mod.parse("no frontmatter here")

    def test_nesting_is_error(self):
        text = "---\nid: x\ntitle: t\nmeta:\n  nested: 1\n---\n"
        with self.assertRaises(CardError):
            card_mod.parse(text)

    def test_unclosed_fence_is_error(self):
        with self.assertRaises(CardError):
            card_mod.parse("---\nid: x\ntitle: t\n")

    def test_bad_status_is_error(self):
        text = MINIMAL.replace("status: active", "status: whatever")
        with self.assertRaises(CardError):
            make_card(text)

    def test_bad_adoption_is_error(self):
        text = MINIMAL.replace("status: active", "status: active\nadoption: always")
        with self.assertRaises(CardError):
            make_card(text)

    def test_section_alias_mixed_header(self):
        text = MINIMAL.replace("## 场景", "## 场景 / Context")
        card = make_card(text)
        self.assertIn("AdGuard", card.section("symptom"))


class TestTokenizer(unittest.TestCase):
    def test_english_words(self):
        self.assertIn("docker", retrieve.tokenize("Docker restart"))

    def test_cjk_bigrams(self):
        tokens = retrieve.tokenize("改配置")
        self.assertIn("改配", tokens)
        self.assertIn("配置", tokens)

    def test_empty(self):
        self.assertEqual(retrieve.tokenize(""), [])


class TestRetrieve(unittest.TestCase):
    def setUp(self):
        self.cards = [make_card(MINIMAL.replace("exp-test-a", "exp-test-a"))]
        self.cards.append(make_card(
            MINIMAL.replace("exp-test-a", "exp-test-b")
            .replace("改配置前先停容器", "端口冲突先查占用者")
            .replace("adguard, 上游, upstream, 配置", "端口, port, 占用")
            .replace("[nas]", "[pc]")
        ))
        self.index = retrieve.Index(self.cards)

    def test_ranks_matching_card_first(self):
        hits = self.index.search("adguard 配置 改了没生效")
        self.assertTrue(hits)
        self.assertEqual(hits[0].card.id, "exp-test-a")

    def test_scope_gate_excludes_other_device(self):
        hits = self.index.search("adguard 配置", device="pc")
        ids = [h.card.id for h in hits]
        self.assertNotIn("exp-test-a", ids)

    def test_scope_any_is_wildcard(self):
        card = make_card(MINIMAL.replace("[nas]", "[any]"))
        index = retrieve.Index([card])
        self.assertTrue(index.search("adguard", device="whatever"))

    def test_not_triggers_penalize(self):
        text = MINIMAL.replace("triggers: [adguard, 上游, upstream, 配置]",
                               "triggers: [adguard, 上游, upstream, 配置]\nnot_triggers: [重装]")
        card = make_card(text)
        index = retrieve.Index([card])
        base = index.search("adguard 配置")[0].score
        penalized = index.search("adguard 配置 重装")[0].score
        self.assertLess(penalized, base)

    def test_confidence_rewards_helped(self):
        plain = make_card(MINIMAL)
        good = make_card(MINIMAL.replace("used: 0", "used: 5").replace("helped: 0", "helped: 5"))
        bad = make_card(MINIMAL.replace("used: 0", "used: 5"))
        self.assertGreater(retrieve.confidence(good), retrieve.confidence(plain))
        self.assertLess(retrieve.confidence(bad), retrieve.confidence(plain))


class TestInject(unittest.TestCase):
    def setUp(self):
        cards = [make_card(MINIMAL)]
        self.hits = retrieve.Index(cards).search("adguard 配置")

    def test_block_is_labelled_reference_only(self):
        block = inject.render(self.hits)
        self.assertIn('authority="reference-only"', block)
        self.assertIn("仅供参考", block)
        self.assertIn("exp-test-a", block)

    def test_budget_is_respected(self):
        for budget in (300, 600, 1200):
            block = inject.render(self.hits, budget=budget)
            self.assertLessEqual(len(block), budget, "budget=%d 被突破" % budget)

    def test_budget_holds_with_many_cards(self):
        cards = [make_card(MINIMAL.replace("exp-test-a", "exp-test-%d" % i))
                 for i in range(6)]
        hits = retrieve.Index(cards).search("adguard 配置 上游")
        for budget in (400, 800, 1200):
            block = inject.render(hits, budget=budget)
            self.assertLessEqual(len(block), budget, "budget=%d 被突破" % budget)

    def test_unverified_shows_not_verified(self):
        block = inject.render(self.hits)
        self.assertIn("未验证", block)

    def test_no_hits_renders_empty(self):
        self.assertEqual(inject.render([]), "")


class TestDoctor(unittest.TestCase):
    def test_stale_card(self):
        text = MINIMAL.replace("status: active", "status: active\nreview_after: 2020-01-01")
        findings = doctor_mod.check([make_card(text)])
        self.assertTrue(any(f["kind"] == "stale" for f in findings))

    def test_duplicate_detection(self):
        a = make_card(MINIMAL)
        b = make_card(MINIMAL.replace("exp-test-a", "exp-test-b"))
        findings = doctor_mod.check([a, b])
        self.assertTrue(any(f["kind"] == "duplicate" for f in findings))

    def test_duplicate_id(self):
        a = make_card(MINIMAL)
        findings = doctor_mod.check([a, a])
        self.assertTrue(any(f["kind"] == "duplicate-id" for f in findings))

    def test_conflict_declared(self):
        text = MINIMAL.replace("status: active",
                               "status: active\nconflicts_with: [exp-other]")
        findings = doctor_mod.check([make_card(text)])
        self.assertTrue(any(f["kind"] == "conflict" for f in findings))


class TestStore(unittest.TestCase):
    def test_seed_library_parses_clean(self):
        cards, problems = store.load_cards(SEEDS)
        self.assertGreaterEqual(len(cards), 15)
        self.assertEqual(problems, [], "种子经验里有格式错误: %s" % (problems,))

    def test_readme_is_not_a_card(self):
        tmp = new_tmp()
        try:
            with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ntitle: x\n---\n")
            cards, problems = store.load_cards(tmp)
            self.assertEqual(cards, [])
            self.assertEqual(problems, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bad_card_does_not_break_others(self):
        tmp = new_tmp()
        try:
            with open(os.path.join(tmp, "good.md"), "w", encoding="utf-8") as fh:
                fh.write(MINIMAL)
            with open(os.path.join(tmp, "bad.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ntitle: no id\n---\n")
            cards, problems = store.load_cards(tmp)
            self.assertEqual(len(cards), 1)
            self.assertEqual(len(problems), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = new_tmp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_copies_seeds(self):
        self.assertEqual(main(["--root", self.tmp, "init"]), 0)
        lessons = os.listdir(os.path.join(self.tmp, "lessons"))
        self.assertGreaterEqual(len(lessons), 15)

    def test_note_creates_draft_and_inbox(self):
        main(["--root", self.tmp, "init"])
        code = main(["--root", self.tmp, "note", "改 AdGuard 配置前要先停容器", "--device", "nas"])
        self.assertEqual(code, 0)
        cards, problems = store.load_cards(os.path.join(self.tmp, "cards"))
        self.assertEqual(problems, [])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].status, "draft")
        with open(os.path.join(self.tmp, "data", "inbox.jsonl"), encoding="utf-8") as fh:
            self.assertEqual(len(fh.readlines()), 1)

    def test_find_returns_nohit_code(self):
        main(["--root", self.tmp, "init"])
        code = main(["--root", self.tmp, "find", "完全不相干的量子计算话题"])
        self.assertEqual(code, 3)

    def test_find_json_shape(self):
        main(["--root", self.tmp, "init"])
        code = main(["--root", self.tmp, "find", "docker compose 启动失败", "--json"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
