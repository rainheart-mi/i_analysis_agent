"""agentscope_proxy.py 语法/结构回归测试 (unittest, 标准库, 不依赖 pytest)。

历史背景：
- 该文件 line 405 写错缩进（"stream_price_band aiter_bytes loop ended" 用了循环外 16sp 缩进，
  但下一行 406 "buffer += chunk" 仍是循环体 20sp 缩进），Python 解析时直接抛
  IndentationError，导致任何 from app.services.agentscope_proxy import ... 都失败，
  进而 uvicorn 子进程崩溃（SpawnProcess-1 traceback）。
- 本测试做两件回归：(1) 文件可被 ast.parse；(2) `buffer += chunk` 必须在
  `async for chunk in resp.aiter_bytes():` 循环体里（保证 in-loop 增量解析，
  与设计注释 #1) 透传 + #2) 行级解析 的顺序一致）。

运行方式（不依赖 pytest）：
    ../i_analysis_agent_env/Scripts/python.exe -m unittest tests.test_agentscope_proxy_syntax -v
"""
from __future__ import annotations

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "services" / "agentscope_proxy.py"


class AgentscopeProxySyntaxTest(unittest.TestCase):
    def test_file_parses(self):
        """整个文件必须可被 ast.parse —— 任何 IndentationError 都会在这里 fail。"""
        src = TARGET.read_text(encoding="utf-8")
        # 解析失败时 ast.parse 会抛 SyntaxError/IndentationError
        ast.parse(src)

    def test_buffer_accumulation_is_inside_async_for(self):
        """`buffer += chunk` 必须在 `async for chunk in resp.aiter_bytes():` 的循环体内。

        设计依据：文件 docstring 与函数注释明确写"增量 + 最终态 on_event 回调"，
        把 buffer 累积和解析放在循环外会让 `on_event` 必须等流结束才触发，丢失实时性。
        """
        tree = ast.parse(TARGET.read_text(encoding="utf-8"))

        func = next(
            (
                n
                for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef)
                and n.name == "stream_price_band_analyze"
            ),
            None,
        )
        self.assertIsNotNone(func, "未找到 stream_price_band_analyze 函数")

        async_for_nodes = [n for n in ast.walk(func) if isinstance(n, ast.AsyncFor)]
        self.assertTrue(async_for_nodes, "stream_price_band_analyze 内未找到 async for 循环")

        # 取每个 async for 循环体的最早子语句行号作为"循环体起点"
        body_min_lineno = min(
            child.lineno
            for node in async_for_nodes
            for child in ast.iter_child_nodes(node)
            if getattr(child, "lineno", None) is not None
        )

        buffer_augassigns = [
            n
            for n in ast.walk(func)
            if isinstance(n, ast.AugAssign)
            and isinstance(n.target, ast.Name)
            and n.target.id == "buffer"
        ]
        self.assertTrue(buffer_augassigns, "未找到 `buffer += chunk` 语句")

        for ba in buffer_augassigns:
            self.assertGreaterEqual(
                ba.lineno,
                body_min_lineno,
                f"buffer += chunk (line {ba.lineno}) 不在 async for 循环体内 "
                f"(应 >= line {body_min_lineno})",
            )


if __name__ == "__main__":
    unittest.main()
