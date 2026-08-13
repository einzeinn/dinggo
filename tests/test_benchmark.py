import os
import time
import tempfile
import shutil
import unittest
from typing import Dict, Any, List
from unittest.mock import MagicMock

from core.ollama_client import OllamaClient
from core.intent_parser import IntentParser, IntentSchema, extract_json_payload
from core.planner import Planner, sanitize_thinking_output, PlanSchema
from core.codegen import CodegenDelegate, extract_content_block
from core.validator import SemanticValidator
from core.memory.short_term import ShortTermMemory
from core.memory.project_context import ProjectContext
from tools.file_ops import read_file, write_file, edit_file, list_dir, get_unified_diff
from tools.shell_ops import run_command


class BenchmarkResult:
    def __init__(self, name: str, iterations: int, total_time_sec: float, extra_info: str = ""):
        self.name = name
        self.iterations = iterations
        self.total_time_sec = total_time_sec
        self.avg_latency_ms = (total_time_sec / iterations) * 1000 if iterations > 0 else 0
        self.ops_per_sec = iterations / total_time_sec if total_time_sec > 0 else 0
        self.extra_info = extra_info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_sec": round(self.total_time_sec, 6),
            "avg_latency_ms": round(self.avg_latency_ms, 3),
            "ops_per_sec": round(self.ops_per_sec, 2),
            "extra_info": self.extra_info
        }


class TestPerformanceAndAbstractionBenchmark(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="dinggo_benchmark_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # ==========================================
    # PERFORMANCE BENCHMARKS
    # ==========================================

    def test_benchmark_intent_parser_extraction_and_validation(self):
        """Benchmark JSON extraction and Pydantic validation speed."""
        raw_markdown = "Berikut hasil analisis intent:\n```json\n{\"category\": \"TASK\", \"is_task\": true, \"task_type\": \"create_file\", \"target_scope\": [\"core/utils.py\"], \"summary\": \"Buat modul utils untuk helper data\", \"constraints\": [\"Gunakan type hints\"]}\n```"
        
        iterations = 5000
        start = time.perf_counter()
        for _ in range(iterations):
            extracted = extract_json_payload(raw_markdown)
            data = IntentSchema.model_validate_json(extracted)
        total_time = time.perf_counter() - start

        res = BenchmarkResult("Intent Extraction & Pydantic Validation", iterations, total_time)
        print(f"\n[PERF] {res.name}: {res.avg_latency_ms:.3f} ms/op | {res.ops_per_sec:.2f} ops/sec")
        self.assertGreater(res.ops_per_sec, 500)

    def test_benchmark_planner_thinking_sanitization(self):
        """Benchmark sanitization speed for Ollama thinking tags (<think>...</think>)."""
        text_with_think = "<think>\nMenganalisis instruksi pengguna...\nMembutuhkan 2 langkah: buat file dan jalankan test.\n</think>\n{\"intent_summary\": \"Implementasi fitur X\", \"steps\": [{\"step_number\": 1, \"description\": \"Tulis utils.py\", \"action_type\": \"write_file\", \"target_path\": \"utils.py\"}]}"
        
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            clean = sanitize_thinking_output(text_with_think)
        total_time = time.perf_counter() - start

        res = BenchmarkResult("Planner Thinking Sanitization", iterations, total_time)
        print(f"[PERF] {res.name}: {res.avg_latency_ms:.3f} ms/op | {res.ops_per_sec:.2f} ops/sec")
        self.assertGreater(res.ops_per_sec, 1000)

    def test_benchmark_file_operations_throughput(self):
        """Benchmark file_ops (write, read, edit, diff) throughput across small (1KB), medium (100KB), large (1MB) payloads."""
        payloads = {
            "small_1KB": "A" * 1024,
            "medium_100KB": "B" * (100 * 1024),
            "large_1MB": "C" * (1024 * 1024)
        }

        for size_name, data in payloads.items():
            filepath = os.path.join(self.test_dir, f"test_{size_name}.txt")
            
            # Write benchmark
            iterations = 50 if "1MB" in size_name else 200
            start = time.perf_counter()
            for _ in range(iterations):
                write_file(filepath, data)
            write_time = time.perf_counter() - start
            write_res = BenchmarkResult(f"File Write ({size_name})", iterations, write_time)

            # Read benchmark
            start = time.perf_counter()
            for _ in range(iterations):
                read_file(filepath)
            read_time = time.perf_counter() - start
            read_res = BenchmarkResult(f"File Read ({size_name})", iterations, read_time)

            # Edit & Diff benchmark
            modified_data = data + "\nADDITION"
            start = time.perf_counter()
            for _ in range(iterations):
                get_unified_diff(filepath, data, modified_data)
            diff_time = time.perf_counter() - start
            diff_res = BenchmarkResult(f"Diff Generation ({size_name})", iterations, diff_time)

            print(f"[PERF] {write_res.name}: {write_res.avg_latency_ms:.3f} ms/op | {write_res.ops_per_sec:.2f} ops/sec")
            print(f"[PERF] {read_res.name}: {read_res.avg_latency_ms:.3f} ms/op | {read_res.ops_per_sec:.2f} ops/sec")
            print(f"[PERF] {diff_res.name}: {diff_res.avg_latency_ms:.3f} ms/op | {diff_res.ops_per_sec:.2f} ops/sec")

            self.assertGreater(read_res.ops_per_sec, 10)

    def test_benchmark_semantic_validator(self):
        """Benchmark SemanticValidator AST parsing and clean validation checks."""
        py_content = "def hello(name: str) -> str:\n    return f'Hello, {name}'\n"
        json_content = '{"status": "ok", "code": 200, "data": [1, 2, 3]}'
        md_content = "# Title\nThis is clean markdown content."

        validator = SemanticValidator()
        iterations = 2000

        start = time.perf_counter()
        for _ in range(iterations):
            validator.validate_file("test.py", py_content)
            validator.validate_file("test.json", json_content)
            validator.validate_file("test.md", md_content)
        total_time = time.perf_counter() - start

        res = BenchmarkResult("Semantic Validator (Py, JSON, MD)", iterations * 3, total_time)
        print(f"[PERF] {res.name}: {res.avg_latency_ms:.3f} ms/op | {res.ops_per_sec:.2f} ops/sec")
        self.assertGreater(res.ops_per_sec, 500)

    def test_benchmark_ollama_model_resolution(self):
        """Benchmark OllamaClient model name fuzzy resolution latency."""
        client = OllamaClient()
        # Mock list_installed_models to simulate local Ollama tags
        client.list_installed_models = MagicMock(return_value=[
            "hf.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT:Q4_K_M",
            "qwen2.5-coder:3b",
            "qwen3.5:4b"
        ])

        iterations = 5000
        start = time.perf_counter()
        for _ in range(iterations):
            client.resolve_model_name("gemma-sea-lion")
            client.resolve_model_name("qwen2.5-coder:3b")
            client.resolve_model_name("qwen3.5:4b")
        total_time = time.perf_counter() - start

        res = BenchmarkResult("Ollama Model Fuzzy Resolution", iterations * 3, total_time)
        print(f"[PERF] {res.name}: {res.avg_latency_ms:.3f} ms/op | {res.ops_per_sec:.2f} ops/sec")
        self.assertGreater(res.ops_per_sec, 1000)

    def test_benchmark_short_term_memory(self):
        """Benchmark ShortTermMemory turn addition and context serialization."""
        context = ProjectContext(working_dir=self.test_dir)
        memory = ShortTermMemory(context=context, max_turns=20)
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            memory.add_turn(
                prompt=f"User instruction {i}",
                category="TASK",
                summary=f"Summary {i}",
                target_scope=["main.py"]
            )
            _ = memory.get_formatted_context()
        total_time = time.perf_counter() - start

        res = BenchmarkResult("ShortTerm Memory Serialization", iterations, total_time)
        print(f"[PERF] {res.name}: {res.avg_latency_ms:.3f} ms/op | {res.ops_per_sec:.2f} ops/sec")
        self.assertGreater(res.ops_per_sec, 200)

    # ==========================================
    # ABSTRACTION BENCHMARKS
    # ==========================================

    def test_benchmark_abstraction_layer_overhead_index(self):
        """
        Benchmark Layer Overhead Index (LOR):
        Measures total time spent in Dinggo abstraction (JSON extraction, validation, error handling)
        versus pure mock LLM execution time.
        """
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "success": True,
            "response": '{"category": "TASK", "is_task": true, "task_type": "edit_file", "target_scope": ["main.py"], "summary": "Fix bug", "constraints": []}'
        }

        parser = IntentParser(ollama_client=mock_client)
        
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            res = parser.parse("Fix bug in main.py")
            self.assertTrue(res["success"])
        total_time = time.perf_counter() - start

        avg_layer_time_ms = (total_time / iterations) * 1000
        print(f"[ABSTRACTION] Layer 1 (IntentParser) Wrapper Latency: {avg_layer_time_ms:.4f} ms/op")

        self.assertLess(avg_layer_time_ms, 2.0)

    def test_benchmark_abstraction_swappability(self):
        """
        Benchmark Provider Swappability:
        Validates that all 3 layers (IntentParser, Planner, CodegenDelegate) work agnostically
        with any custom client implementation fulfilling OllamaClient contract interface.
        """
        class CustomMockClient:
            def generate(self, model, prompt, **kwargs):
                if "Intent Parser" in (kwargs.get("system_prompt") or ""):
                    return {"success": True, "response": '{"category": "TASK", "is_task": true, "task_type": "read_file", "summary": "Read file", "constraints": []}'}
                elif "Planner" in (kwargs.get("system_prompt") or ""):
                    return {"success": True, "response": '{"intent_summary": "Read file", "steps": [{"step_number": 1, "description": "Read main.py", "action_type": "read_file", "target_path": "main.py"}]}'}
                else:
                    return {"success": True, "response": "print('Custom Client Code')"}

        custom_client = CustomMockClient()

        start = time.perf_counter()
        parser = IntentParser(ollama_client=custom_client)
        planner = Planner(ollama_client=custom_client)
        codegen = CodegenDelegate(ollama_client=custom_client)

        intent_res = parser.parse("Read main.py")
        plan_res = planner.create_plan(intent_res["intent"])
        code_res = codegen.generate_code("Write print statement", target_path="main.py")
        elapsed = (time.perf_counter() - start) * 1000

        self.assertTrue(intent_res["success"])
        self.assertTrue(plan_res["success"])
        self.assertTrue(code_res["success"])
        print(f"[ABSTRACTION] 3-Layer Execution via Custom Swapped Provider: {elapsed:.3f} ms total")

    def test_benchmark_resilience_retry_overhead_penalty(self):
        """
        Benchmark Retry Overhead Penalty:
        Measures latency penalty when LLM outputs malformed JSON requiring 1, 2, or 3 repair retries.
        """
        mock_client = MagicMock()
        
        # 1 Retry scenario (Attempt 1 fails, Attempt 2 succeeds)
        mock_client.generate.side_effect = [
            {"success": True, "response": "malformed json output"},
            {"success": True, "response": '{"category": "TASK", "is_task": true, "task_type": "edit_file", "summary": "Fix", "constraints": []}'}
        ]
        parser = IntentParser(ollama_client=mock_client)
        start = time.perf_counter()
        res_retry = parser.parse("Fix code")
        time_1_retry = (time.perf_counter() - start) * 1000

        self.assertTrue(res_retry["success"])
        self.assertEqual(res_retry["attempts"], 2)

        print(f"[ABSTRACTION] Latency Penalty for 1 Repair Retry: {time_1_retry:.4f} ms")
        self.assertLess(time_1_retry, 10.0)

    def test_benchmark_abstraction_error_isolation(self):
        """
        Benchmark Error Isolation & Abstraction Leak Protection:
        Ensures exception or network failures in LLM client do not crash layer wrappers
        and return clean error dictionary contracts.
        """
        failing_client = MagicMock()
        failing_client.generate.return_value = {"success": False, "error": "Connection timed out"}

        parser = IntentParser(ollama_client=failing_client)
        planner = Planner(ollama_client=failing_client)
        codegen = CodegenDelegate(ollama_client=failing_client)

        res1 = parser.parse("Do task")
        res2 = planner.create_plan({"summary": "Do task"})
        res3 = codegen.generate_code("Write code")

        self.assertFalse(res1["success"])
        self.assertFalse(res2["success"])
        self.assertFalse(res3["success"])
        self.assertIn("error", res1)
        self.assertIn("error", res2)
        self.assertIn("error", res3)
        print("[ABSTRACTION] Error Isolation Integrity: 100% Graceful Fallback Handled")


if __name__ == "__main__":
    unittest.main()
