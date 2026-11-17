"""Command line:

  python -m bulten run --edition gundem                 # prepare slides + caption only (no publishing)
  python -m bulten run --edition gundem --publish --wait  # what the scheduled workflow does
  python -m bulten run --edition gundem --issue samples/gundem2.json   # skip the AI, test rendering
  python -m bulten candidates --edition spor            # show today's candidate headlines
"""
import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore", module="urllib3")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bulten")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--edition", required=True, choices=["gundem", "ekonomi", "spor"])
    r.add_argument("--publish", action="store_true", help="post to Instagram")
    r.add_argument("--wait", action="store_true", help="wait until the edition's publish time")
    r.add_argument("--force", action="store_true", help="publish even if this edition already ran today")
    r.add_argument("--issue", help="use a ready issue JSON instead of collecting and writing")
    c = sub.add_parser("candidates")
    c.add_argument("--edition", required=True, choices=["gundem", "ekonomi", "spor"])
    args = p.parse_args(argv)

    if args.cmd == "candidates":
        from .collect import collect
        for i in collect(args.edition):
            print(f"[{len(i['sources'])}] {i['published']}  {i['title']}  — {', '.join(i['sources'][:3])}")
        return 0

    from .pipeline import Skip, run
    try:
        result = run(args.edition, publish=args.publish, wait=args.wait, force=args.force, issue_file=args.issue)
    except Skip as exc:
        print(f"[run] atlandı: {exc}")
        return 0
    print(json.dumps({k: v for k, v in result.items() if k != "caption"}, ensure_ascii=False, indent=1))
    print("\n--- caption ---\n" + result["caption"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
