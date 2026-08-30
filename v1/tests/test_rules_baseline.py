import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_rules_baseline.py"
SPEC = importlib.util.spec_from_file_location("run_rules_baseline", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_rules_cover_core_patterns() -> None:
    assert MODULE.raw_rule("MIT")[0] == "short_circuit"
    assert MODULE.raw_rule("UCLA vs USC")[0] == "complex"
    assert MODULE.raw_rule("schools with normal people")[0] == "llm_needed"
    assert MODULE.raw_rule("colleges in California")[0] == "medium"
