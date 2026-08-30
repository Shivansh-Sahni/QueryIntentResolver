from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .resolver import QueryIntentResolver


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve one raw query into a Query Intent Resolver V1 route")
    parser.add_argument("query", nargs="?", help="Raw query text. Reads stdin when omitted.")
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("v1/artifacts/release/model.joblib"),
        help="Path to the packaged model.joblib",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("v1/config/route_policy.json"),
        help="Path to route_policy.json",
    )
    parser.add_argument("--debug", action="store_true", help="Include reserved/debug fields")
    args = parser.parse_args()

    query = args.query if args.query is not None else sys.stdin.read().strip()
    resolver = QueryIntentResolver(model_path=args.model, policy_path=args.policy)
    result = resolver.resolve(query, include_optional_fields=args.debug)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
