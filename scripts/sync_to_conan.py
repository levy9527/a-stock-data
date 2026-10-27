#!/usr/bin/env python3
"""把 a-stock-data skill 同步进 ai-conan-admin（默认落到 backend/skills/a-stock-data）。

设计要点：
- 幂等：目标目录是纯镜像，只按白名单复制，多余文件（含旧版遗留的 tests/docs）会被清掉。
- 不落元数据：不写 manifest，目标目录只有 SKILL.md + references + scripts。
- 可检测：`--check` 逐文件比对上游与目标的 sha256，并报出目标多余文件，漂移即非零退出。
- 可验证：`--verify` 跑离线 unittest + runtime 真实取数冒烟 + 后端 pytest。
- 不替你提交：默认只写文件；`--commit` 才在 lights 子模块里 git commit（不 push）。

常用：
    python3 scripts/sync_to_conan.py --check
    python3 scripts/sync_to_conan.py --deps --verify
    python3 scripts/sync_to_conan.py --commit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = Path(os.environ.get("CONAN_PROJECT_ROOT", "/Users/levy/PycharmProjects/ai-conan-admin"))
DEST_REL = "backend/skills/a-stock-data"

# 复制白名单（顶层条目；目录递归）。assets/ 是赞助二维码，与运行时无关，不同步。
# 只同步运行时资产：SKILL.md + references + 取数运行时。
# tests/ docs/ CHANGELOG/ README/ LICENSE 属于上游开发与法务物，不进下游运行时目录
# （离线测试改为在上游仓跑）；也不写 manifest：--check 直接逐文件比对 hash。
COPY_ENTRIES = ("SKILL.md", "references", "scripts")
SKIP_NAMES = {"__pycache__", ".DS_Store", ".git", ".idea", ".pi"}
SKIP_FILES = {"scripts/sync_to_conan.py"}

REQUIRED_DEPS = ("mootdx", "baostock", "stockstats")
INFO_DEPS = ("requests", "pandas", "numpy", "xlrd", "openpyxl")
# mootdx 硬钉 httpx>=0.25,<0.26，与后端 httpx>=0.28 直接冲突（agno/openai 要求新版）。
# 它的取数走 TCP（tdxpy），不真用 httpx，所以 --no-deps 装本体 + 显式补齐它要的旁支依赖。
NO_DEPS_PACKAGES = ("mootdx", "baostock", "stockstats")
MOOTDX_EXTRAS = (
    "click>=8.1.3,<9",
    "prettytable>=3.5,<4",
    "py-mini-racer>=0.6,<0.7",
    "tdxpy>=0.2.5,<0.3",
    "tenacity>=8.1,<9",
    "tqdm",
    "typing-extensions>=4.5,<5",
)
HTTPX_MIN = (0, 28)


# ---------- 基础工具 ----------


def git(*args: str, cwd: Path) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(source: Path) -> dict[str, Path]:
    """白名单内、按相对路径索引的文件集合。"""
    files: dict[str, Path] = {}
    for entry in COPY_ENTRIES:
        path = source / entry
        if path.is_file():
            files[entry] = path
            continue
        if not path.is_dir():
            continue
        for child in sorted(path.rglob("*")):
            if not child.is_file() or child.name in SKIP_NAMES:
                continue
            if any(part in SKIP_NAMES for part in child.relative_to(source).parts):
                continue
            rel = child.relative_to(source).as_posix()
            if rel in SKIP_FILES:
                continue
            files[rel] = child
    return files


def target_dest(target: Path, dest_name: str) -> Path:
    return target / dest_name


def venv_python(target: Path) -> Path:
    return target / "backend" / ".venv" / "bin" / "python"


# ---------- 动作 ----------


def do_check(source: Path, dest: Path) -> int:
    """目标目录是纯镜像：逐文件比对源码与目标的 sha256，不依赖额外元数据文件。"""
    files = collect(source)
    if not (dest / "SKILL.md").is_file():
        print(f"[check] {dest} 未同步过（缺 SKILL.md）")
        return 1
    problems = []
    missing = sorted(rel for rel in files if not (dest / rel).is_file())
    stale = [rel for rel, path in files.items() if (dest / rel).is_file() and sha256(path) != sha256(dest / rel)]
    extra = sorted(set(_target_files(dest)) - set(files))
    if missing:
        problems.append(f"目标缺文件 {len(missing)} 个：{', '.join(missing[:6])}")
    if stale:
        problems.append(f"内容不同 {len(stale)} 个：{', '.join(stale[:6])}{' …' if len(stale) > 6 else ''}")
    if extra:
        problems.append(f"目标多余 {len(extra)} 个：{', '.join(extra[:6])}")
    if not problems:
        print(f"[check] 已最新（{len(files)} 个文件）")
        return 0
    print(f"[check] 需要同步 → {dest}")
    for item in problems:
        print(f"  - {item}")
    print("  跑：python3 scripts/sync_to_conan.py")
    return 1


def _target_files(dest: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not dest.is_dir():
        return files
    for path in dest.rglob("*"):
        if path.is_file() and not any(part in SKIP_NAMES for part in path.relative_to(dest).parts):
            files[path.relative_to(dest).as_posix()] = path
    return files


def do_sync(source: Path, dest: Path, dry_run: bool) -> int:
    files = collect(source)
    if dry_run:
        print(f"[sync] dry-run：将写入 {len(files)} 个文件 → {dest}")
        for rel in sorted(files):
            print(f"  + {rel}")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    for rel, path in files.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    # 目标目录是纯镜像：清掉不属于本次同步的文件（含旧版遗留的 tests/docs/manifest）
    removed = sorted(set(_target_files(dest)) - set(files))
    for rel in removed:
        stale = dest / rel
        if stale.is_file():
            stale.unlink()
            try:
                stale.parent.rmdir()
            except OSError:
                pass
    # 我方目录内的字节码缓存不属于同步内容（测试跑过会留下）
    for cache in sorted(dest.rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache, ignore_errors=True)
    for leftover in sorted(dest.iterdir()):  # 清掉因残留而空不掉的目录
        if leftover.is_dir() and not any(leftover.rglob("*")):
            shutil.rmtree(leftover, ignore_errors=True)
    commit = git("rev-parse", "--short", "HEAD", cwd=source)
    print(f"[sync] 写入 {len(files)} 个文件 → {dest}" + (f"（清理 {len(removed)} 个）" if removed else ""))
    print(f"[sync] 上游 {git('remote', 'get-url', 'origin', cwd=source) or source} @ {commit or '?'}{' (dirty)' if git('status', '--porcelain', cwd=source) else ''}")
    toplevel = git("rev-parse", "--show-toplevel", cwd=dest)
    if toplevel:
        print(f"[sync] 提醒：{toplevel} 是 git 仓库，请自行提交；父仓还需 git add backend/skills 升 gitlink")
    return 0


def do_deps(target: Path) -> int:
    python = venv_python(target)
    if not python.is_file():
        print(f"[deps] 未找到 {python}")
        return 1
    probe = (
        "import importlib.util as u, json;"
        f"req={list(REQUIRED_DEPS)!r}; info={list(INFO_DEPS)!r};"
        "print(json.dumps({'missing': [m for m in req if u.find_spec(m) is None],"
        " 'info': [m for m in info if u.find_spec(m) is None]}))"
    )
    out = subprocess.run([str(python), "-c", probe], capture_output=True, text=True)
    if out.returncode != 0:
        print(f"[deps] 探测失败：{out.stderr.strip()[:400]}")
        return 1
    state = json.loads(out.stdout.strip() or "{}")
    if state.get("info"):
        print(f"[deps] 注意：缺少（部分端点会不可用）{', '.join(state['info'])}")
    missing = state.get("missing") or []
    if not missing:
        print(f"[deps] 依赖齐全（{', '.join(REQUIRED_DEPS)}）")
        return _guard_httpx(python)
    print(f"[deps] 安装 {', '.join(missing)} → {python}")
    # uv 建的 venv 默认没有 pip；有 uv 就用 uv pip，且落回项目自己的 venv。
    uv = shutil.which("uv")
    install = (
        (lambda *pkgs: subprocess.run([uv, "pip", "install", "--python", str(python), *pkgs], text=True).returncode)
        if uv
        else (lambda *pkgs: subprocess.run([str(python), "-m", "pip", "install", *pkgs], text=True).returncode)
    )
    code = install("--no-deps", *missing) if uv else install(*missing)
    if code != 0:
        return code
    if any(pkg in NO_DEPS_PACKAGES for pkg in missing) and install(*MOOTDX_EXTRAS) != 0:
        return 1
    return _guard_httpx(python)


def _guard_httpx(python: Path) -> int:
    """装完检查 httpx 没被 mootdx 拖回旧版；被降级就恢复到项目要求的下限。"""
    out = subprocess.run([str(python), "-c", "import httpx; print(httpx.__version__)"], capture_output=True, text=True)
    version = out.stdout.strip()
    try:
        major, minor = (int(part) for part in version.split(".")[:2])
    except ValueError:
        print(f"[deps] 无法识别 httpx 版本：{version!r}")
        return 1
    if (major, minor) >= HTTPX_MIN:
        print(f"[deps] httpx {version} 保持项目要求（>=0.28）")
        return 0
    print(f"[deps] 警告：httpx 被降级到 {version}，恢复 >=0.28")
    uv = shutil.which("uv")
    cmd = [uv, "pip", "install", "--python", str(python), "httpx>=0.28"] if uv else [str(python), "-m", "pip", "install", "httpx>=0.28"]
    return subprocess.run(cmd, text=True).returncode


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    out = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    text = (out.stdout or "") + (out.stderr or "")
    return out.returncode, text.strip()


def _summary(text: str) -> str:
    """从测试输出里挑出结果行（passed/failed/OK/FAILED），跳 coverage 噪声。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if re.search(r"\b\d+ (passed|failed|error)|\b0 tests|\b\d+ tests? (passed|failed)", line):
            return line
    for line in reversed(lines):
        if line.startswith("OK") or line.startswith("FAILED"):
            return line
    return lines[-1] if lines else ""


def do_verify(source: Path, target: Path, dest: Path, live: bool) -> int:
    python = venv_python(target)
    if not python.is_file():
        print(f"[verify] 未找到 {python}")
        return 1
    failures = 0

    if not (dest / "SKILL.md").is_file():
        print(f"[verify] 目标无 SKILL.md：{dest}（先跑同步）")
        return 1

    # 离线测试跑在上游仓（tests/ 不下发），验证的是「即将同步的那份 md」
    code, text = _run([str(python), "-m", "unittest", "discover", "-s", "tests", "-q"], source)
    print(f"[verify] 离线测试 {'PASS' if code == 0 else 'FAIL'}：{_summary(text)}")
    failures += code != 0

    if live:
        code, text = _run([str(python), "scripts/astock_runtime.py", "--layers", "01-quote", "--smoke"], dest)
        print(f"[verify] 真实取数冒烟 {'PASS' if code == 0 else 'FAIL'}：{text.splitlines()[-1] if text else ''}")
        failures += code != 0
    else:
        print("[verify] 真实取数冒烟 SKIP（--no-live）")

    test_file = target / "backend" / "tests" / "test_a_stock_data_skill.py"
    if test_file.is_file():
        code, text = _run([str(python), "-m", "pytest", str(test_file), "-q"], target / "backend")
        print(f"[verify] 后端集成测试 {'PASS' if code == 0 else 'FAIL'}：{_summary(text)}")
        failures += code != 0
    else:
        print(f"[verify] 后端集成测试 SKIP（未找到 {test_file.name}）")

    print(f"[verify] 结论：{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 0 if failures == 0 else 1


def do_commit(dest: Path, source: Path) -> int:
    toplevel = git("rev-parse", "--show-toplevel", cwd=dest)
    if not toplevel:
        print(f"[commit] {dest} 不在 git 仓库内，跳过")
        return 1
    rel = dest.relative_to(toplevel).as_posix()
    head = git("rev-parse", "HEAD", cwd=source)
    git("add", rel, cwd=Path(toplevel))
    code = subprocess.run(
        ["git", "commit", "-m", f"feat(skills): add a-stock-data (synced from {head[:8]})"],
        cwd=toplevel,
        capture_output=True,
        text=True,
    )
    print(f"[commit] {toplevel}: {code.stdout.strip().splitlines()[-1] if code.stdout.strip() else code.stderr.strip()[:300]}")
    print("[commit] 未 push；父仓仍需 git add backend/skills 升 gitlink")
    return code.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="同步 a-stock-data skill 到 ai-conan-admin")
    parser.add_argument("--source", default=str(SOURCE_ROOT), help="上游 skill 目录（默认本仓根）")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help=f"目标项目根（默认 {DEFAULT_TARGET}）")
    parser.add_argument("--dest-name", default=DEST_REL, help=f"目标相对路径（默认 {DEST_REL}）")
    parser.add_argument("--check", action="store_true", help="只检查漂移，不写文件")
    parser.add_argument("--deps", action="store_true", help="在目标 backend/.venv 补装缺的依赖")
    parser.add_argument("--verify", action="store_true", help="离线测试 + 取数冒烟 + 后端测试")
    parser.add_argument("--no-live", action="store_true", help="--verify 时跳过真实取数冒烟")
    parser.add_argument("--commit", action="store_true", help="同步后在目标 git 仓内提交（不 push）")
    parser.add_argument("--dry-run", action="store_true", help="只打印将写入的文件")
    args = parser.parse_args(argv)

    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()
    dest = target_dest(target, args.dest_name)
    if not (source / "SKILL.md").is_file():
        print(f"[sync] 源目录不像 skill：{source}")
        return 1
    if not target.is_dir():
        print(f"[sync] 目标不存在：{target}")
        return 1

    if args.check:
        return do_check(source, dest)
    if args.deps:
        return do_deps(target)
    if args.verify:
        return do_verify(source, target, dest, live=not args.no_live)

    code = do_sync(source, dest, dry_run=args.dry_run)
    if code != 0 or args.dry_run:
        return code
    if args.commit:
        return do_commit(dest, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
