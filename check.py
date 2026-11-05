#!/usr/bin/env python3
"""一键自检：测试 + 零依赖断言 + 泄露面审计。

按自己项目的规矩来：能被机器守的承诺，不要留在人的记忆里。
  * "零第三方依赖" → 扫 AST，比 import 名单
  * "不带私密信息"   → 正则扫，审计工具本身不含秘密
"""

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 审计用的都是**通用类别**，不放具体秘密。
LEAK_PATTERNS = (
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"), "GitHub token"),
    (re.compile(r"\bms-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "ModelScope token"),
    (re.compile(r"\b[0-9a-f]{32}\b"), "疑似 32 位十六进制令牌"),
    (re.compile(r"(?i)(password|passwd|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{3,}['\"]"), "硬编码口令"),
    # 内网地址：只允许回环与未指定地址；示例一律用 RFC 5737 文档段
    (re.compile(r"\b(?:10|127|169\.254|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
     "内网/保留地址"),
)
ALLOW_LOCAL = {"127.0.0.1", "0.0.0.0", "localhost"}

SKIP_DIRS = {".git", "__pycache__", ".venv", "build", "dist", ".shiftbook",
             ".tmp-test", ".demo"}
SCAN_EXT = {".py", ".md", ".json", ".jsonl", ".toml", ".yml", ".yaml", ".txt"}


def iter_files(root, exts=None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if exts and os.path.splitext(name)[1].lower() not in exts:
                continue
            yield os.path.join(dirpath, name)


# ── 1. 测试 ──────────────────────────────────────────────────

def run_tests():
    print("[1/3] 单元测试")
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                          cwd=HERE)
    if proc.returncode != 0:
        print("  单元测试失败")
        return False
    print("  通过")
    return True


# ── 2. 零依赖 ────────────────────────────────────────────────

def check_zero_deps():
    print("[2/3] 零第三方依赖")
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    if not stdlib:
        print("  Python < 3.10，跳过（sys.stdlib_module_names 不可用）")
        return True
    bad = []
    for path in iter_files(HERE, {".py"}):
        if os.sep + "tests" + os.sep in path or os.sep + "demo" + os.sep in path:
            continue
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name and name not in stdlib and name != "shiftbook":
                    bad.append((path, name))
    if bad:
        for path, name in bad:
            print("  非标准库依赖: %s -> %s" % (path, name))
        return False
    # 元数据里写了依赖，pip 装的时候照样会拉下来，承诺一样破
    pyproject = os.path.join(HERE, "pyproject.toml")
    if os.path.exists(pyproject):
        try:
            import tomllib
        except ImportError:      # Python < 3.11：没有 tomllib，跳过这一条
            print("  Python < 3.11，跳过 pyproject 依赖核对")
            return True
        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        deps = data.get("project", {}).get("dependencies") or []
        if deps:
            print("  pyproject.toml 声明了运行时依赖: %s" % deps)
            return False
    print("  通过：全部标准库")
    return True


# ── 3. 泄露面 ────────────────────────────────────────────────

def check_no_leaks():
    print("[3/3] 泄露面审计")
    hits = []
    for path in iter_files(HERE, SCAN_EXT):
        rel = os.path.relpath(path, HERE)
        if rel.startswith("check.py"):
            continue  # 审计工具含正则，不含秘密
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(lines, start=1):
            for pattern, label in LEAK_PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(0)
                    if label == "内网/保留地址" and value in ALLOW_LOCAL:
                        continue
                    hits.append((rel, lineno, label, value))
    if hits:
        for rel, lineno, label, value in hits[:20]:
            print("  %s:%d [%s] %s" % (rel, lineno, label, value))
        print("  共 %d 处" % len(hits))
        return False
    print("  通过：没有令牌、口令、内网地址")
    return True


def main():
    checks = [run_tests(), check_zero_deps(), check_no_leaks()]
    print("")
    if all(checks):
        print("全绿。")
        return 0
    print("有检查未通过。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
