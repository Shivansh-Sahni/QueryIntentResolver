from __future__ import annotations
import argparse,json,sys
from .runtime import Resolver

def main():
    p=argparse.ArgumentParser(description="Run the query-only resolver without API credentials or downstream calls")
    p.add_argument("query",nargs="?")
    p.add_argument("--bundle")
    args=p.parse_args()
    try:
        r=Resolver(args.bundle)
        if args.query is not None:
            print(json.dumps(r.resolve(args.query),allow_nan=False))
        else:
            for line in sys.stdin:
                if line.strip(): print(json.dumps(r.resolve(line.rstrip("\n")),allow_nan=False))
    except (OSError,ValueError) as e:
        print(f"Resolver error: {e}",file=sys.stderr)
        raise SystemExit(2)

if __name__=="__main__": main()
