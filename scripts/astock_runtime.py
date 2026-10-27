#!/usr/bin/env python3
"""把 `references/**/*.md` 里的端点代码变成可直接调用的函数，零副作用导入。

为什么不是 `exec` 原文：各层 md 的代码块里带 demo 调用（打印、真发请求），
整段 exec 会在 import 阶段打网络、刷屏。这里只保留「声明类」语句：
import / def / class / 纯常量赋值；带端点调用的赋值一律当 demo 丢弃，
初始化失败也只跳过该常量而不是拖垮整层。缺依赖（mootdx / baostock）
只影响该层对应端点。

用法：
    from astock_runtime import load
    ns = load(["01-quote"])
    ns["tencent_quote"](["600519"])      # 或 ns.tencent_quote([...])

命令行：
    python scripts/astock_runtime.py --list
    python scripts/astock_runtime.py --layers 01-quote --smoke
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
COMMON_KEY = "01-common"
_COMMON_FILE = "01-common.md"
_FENCE = re.compile(r"^```python[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
_DECLARATIONS = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_ASSIGNMENTS = (ast.Assign, ast.AnnAssign)
# 顶层赋值里允许出现的「纯计算」名字。只要出现其它裸名调用（尤其是本 skill 自己定义的
# 端点函数），就判定为 md 里的 demo 代码，直接丢弃——否则 import 会真发请求甚至阻塞。
_SAFE_CALLS = frozenset({
    "set", "list", "dict", "tuple", "frozenset", "len", "str", "int", "float", "bool",
    "sorted", "range", "sum", "min", "max", "zip", "enumerate", "reversed", "abs",
    "timezone", "timedelta", "Counter", "defaultdict", "OrderedDict", "datetime", "date",
})
_CACHE: Dict[Tuple[str, ...], "Namespace"] = {}


class Namespace(dict):
    """端点命名空间：dict 取值 + 属性访问 + 加载期错误清单。"""

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(f"{name} 未加载；先 load() 对应层，或查 .errors") from exc

    @property
    def errors(self) -> List[Dict]:
        return self.get("__errors__") or []


def _iter_fences(text: str) -> Iterable[Tuple[int, str]]:
    for index, block in enumerate(_FENCE.findall(text)):
        yield index, block


def _wrap_assignment(node: ast.stmt) -> ast.stmt:
    """赋值失败（缺依赖 / 建连接 / 拉常量）时静默跳过，不阻断后续声明。"""
    handler = ast.ExceptHandler(
        type=ast.Name(id="Exception", ctx=ast.Load()),
        name="__runtime_error__",
        body=[ast.Pass()],
    )
    return ast.Try(body=[node], handlers=[handler], orelse=[], finalbody=[])


def _is_constant_assignment(node: ast.stmt) -> bool:
    """常量初始化（字面量 / 容器推导 / requests.Session() 这类属性调用）才保留。"""
    value = node.value
    if value is None:
        return False
    for child in ast.walk(value):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id not in _SAFE_CALLS:
            return False
    return True


def _harden(node: ast.stmt) -> List[ast.stmt]:
    """递归裁剪代码块：保留声明与赋值，丢弃 demo / 打印 / 顶层调用。"""
    if isinstance(node, _DECLARATIONS):
        return [node]
    if isinstance(node, _ASSIGNMENTS):
        return [_wrap_assignment(node)] if _is_constant_assignment(node) else []
    if isinstance(node, ast.Try):  # 可选依赖的 try-import
        body = [stmt for child in node.body for stmt in _harden(child)]
        if not body:
            return []
        handlers = []
        for handler in node.handlers:
            rebuilt = [stmt for child in handler.body for stmt in _harden(child)]
            handlers.append(ast.ExceptHandler(type=handler.type, name=handler.name, body=rebuilt or [ast.Pass()]))
        orelse = [stmt for child in node.orelse for stmt in _harden(child)]
        finalbody = [stmt for child in node.finalbody for stmt in _harden(child)]
        return [_wrap_assignment(ast.Try(body=body, handlers=handlers, orelse=orelse, finalbody=finalbody))]
    return []


def _compile_block(block: str, origin: str) -> Optional[ast.Module]:
    tree = ast.parse(block, filename=origin)
    body = [stmt for node in tree.body for stmt in _harden(node)]
    if not body:
        return None
    return ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))


def _exec_file(path: Path, namespace: dict, errors: List[Dict]) -> int:
    """执行单个 md 的全部代码块，返回成功块数。"""
    ok = 0
    for index, block in _iter_fences(path.read_text(encoding="utf-8")):
        origin = f"{path.relative_to(SKILL_ROOT)}#{index}"
        try:
            module = _compile_block(block, origin)
            if module is None:
                continue
            exec(compile(module, origin, "exec"), namespace)
            ok += 1
        except Exception as exc:  # 缺依赖、3.9 兼容等：记录但不中断
            errors.append({"origin": origin, "type": type(exc).__name__, "message": str(exc)[:300]})
    return ok


def _layer_files() -> Dict[str, Path]:
    """key → md 路径。layer 支持全名（01-quote）、短名（quote）、序号（01）。"""
    mapping: Dict[str, Path] = {}
    for path in sorted(REFERENCES.rglob("*.md")):
        rel = path.relative_to(REFERENCES).as_posix()
        if rel == _COMMON_FILE:
            continue
        key = rel[len("layers/"):] if rel.startswith("layers/") else rel
        stem = key[: -len(".md")] if key.endswith(".md") else key
        mapping.setdefault(stem, path)
        if stem[:2].isdigit() and stem[2:3] == "-":
            mapping.setdefault(stem[3:], path)
            mapping.setdefault(stem[:2], path)
    return mapping


def available_layers() -> List[str]:
    return sorted({p.name for p in REFERENCES.rglob("*.md") if p.name != _COMMON_FILE})


def _resolve(layer: str) -> Path:
    files = _layer_files()
    key = layer.strip()
    if key.startswith("layers/"):
        key = key[len("layers/"):]
    if key.endswith(".md"):
        key = key[: -len(".md")]
    path = files.get(key)
    if path is None:
        raise KeyError(f"未找到层 {layer!r}；可用：{', '.join(sorted(files))}")
    return path


def load(layers: Optional[Iterable[str]] = None, *, common: bool = True, reload: bool = False) -> Namespace:
    """加载指定层（默认全部）。返回 Namespace，可 dict 取值或属性访问。"""
    keys = list(_layer_files()) if layers is None else [str(layer) for layer in layers]
    paths: List[Path] = []
    if common:
        paths.append(REFERENCES / _COMMON_FILE)
    for key in keys:
        path = _resolve(key)
        if path not in paths:  # keys 里有别名，去重
            paths.append(path)
    cache_key = tuple(str(path) for path in paths)
    if not reload and cache_key in _CACHE:
        return _CACHE[cache_key]

    namespace: dict = {}
    errors: List[Dict] = []
    block_count = 0
    for path in paths:
        block_count += _exec_file(path, namespace, errors)
    namespace["__errors__"] = errors
    namespace["__sources__"] = [path.relative_to(SKILL_ROOT).as_posix() for path in paths]
    namespace["__blocks__"] = block_count
    result = Namespace(namespace)
    _CACHE[cache_key] = result
    return result


def smoke(code: str = "600519") -> dict:
    """真实取数冒烟：腾讯实时行情。返回证据字典，失败抛 RuntimeError。"""
    ns = load(["01-quote"])
    quote = ns.tencent_quote([code])
    row = quote.get(code) or (next(iter(quote.values())) if isinstance(quote, dict) and quote else None)
    if not row:
        raise RuntimeError(f"tencent_quote({code}) 返回空；加载错误：{ns.errors}")
    price = row.get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        raise RuntimeError(f"tencent_quote({code}) 价格异常：{price!r}")
    return {"code": code, "name": row.get("name"), "price": price, "pe_ttm": row.get("pe_ttm"), "is_stale": row.get("is_stale")}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="a-stock-data 端点运行时")
    parser.add_argument("--layers", help="逗号分隔的层（如 01-quote,06-fundamentals）；缺省加载全部")
    parser.add_argument("--list", action="store_true", help="列出可用层")
    parser.add_argument("--names", action="store_true", help="列出已加载的可调用函数")
    parser.add_argument("--smoke", action="store_true", help="真实取数冒烟（腾讯 600519）")
    parser.add_argument("--code", default="600519", help="冒烟用的代码")
    args = parser.parse_args(argv)

    if args.list:
        for name in available_layers():
            print(name)
        return 0

    layers = [item.strip() for item in args.layers.split(",") if item.strip()] if args.layers else None
    ns = load(layers)
    print(f"layers={ns['__sources__']} blocks={ns['__blocks__']} errors={len(ns.errors)}")
    for item in ns.errors:
        print(f"  ! {item['origin']} {item['type']}: {item['message'][:120]}")
    if args.names:
        for name in sorted(ns):
            if callable(ns[name]) and not name.startswith("__"):
                print(name)
    if args.smoke:
        print(smoke(args.code))
    return 0


if __name__ == "__main__":
    sys.exit(main())
