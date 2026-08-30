from __future__ import annotations

import json
import sys

import numpy as np

from qir_v1 import cli


class FakeResolver:
    def __init__(self, *args, **kwargs):
        pass

    def resolve(self, query, include_optional_fields=False):
        assert query == "MIT"
        return {"route": "short_circuit", "confidence": 0.9}


def test_cli_emits_contract_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "QueryIntentResolver", FakeResolver)
    monkeypatch.setattr(sys, "argv", ["qir-resolve", "MIT"])
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result == {"route": "short_circuit", "confidence": 0.9}
