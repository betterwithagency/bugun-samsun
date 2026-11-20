"""Command line:

  python -m bulten run --edition gundem                 # prepare slides + caption only (no publishing)
  python -m bulten run --edition gundem --publish --wait  # what the scheduled workflow does
  python -m bulten run --edition gundem --issue samples/gundem2.json   # skip the AI, test rendering
  python -m bulten run --edition reels --publish --wait  # 17.30 Reels from today's Gündem bulletin
  python -m bulten candidates --edition spor            # show today's candidate headlines
  python -m bulten check                                 # verify credentials, followers, trial Reels (posts nothing)
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
    r.add_argument("--edition", required=True, choices=["gundem", "ekonomi", "spor", "reels"])
    r.add_argument("--publish", action="store_true", help="post to Instagram")
    r.add_argument("--wait", action="store_true", help="wait until the edition's publish time")
    r.add_argument("--force", action="store_true", help="publish even if this edition already ran today")
    r.add_argument("--issue", help="use a ready issue JSON instead of collecting and writing")
    c = sub.add_parser("candidates")
    c.add_argument("--edition", required=True, choices=["gundem", "ekonomi", "spor"])
    sub.add_parser("check")
    args = p.parse_args(argv)

    if args.cmd == "check":
        return check()

    if args.cmd == "candidates":
        from .collect import collect
        for i in collect(args.edition):
            print(f"[{len(i['sources'])}] {i['published']}  {i['title']}  — {', '.join(i['sources'][:3])}")
        return 0

    from .pipeline import Skip, run
    if args.edition == "reels":
        from .reels import run as run_reels
        run = lambda edition, **kw: run_reels(**kw)  # noqa: E731
    try:
        result = run(args.edition, publish=args.publish, wait=args.wait, force=args.force, issue_file=args.issue)
    except Skip as exc:
        print(f"[run] atlandı: {exc}")
        return 0
    print(json.dumps({k: v for k, v in result.items() if k != "caption"}, ensure_ascii=False, indent=1))
    print("\n--- caption ---\n" + result["caption"])
    return 0


def check() -> int:
    """Confirm the secrets work without publishing anything. Never prints secret values."""
    import os

    ok = True
    from . import instagram, tokens
    try:
        token = tokens.get_token()
    except Exception as exc:
        token = None
        ok = False
        print(f"[check] Instagram HATA: {exc}")
    if token:
        try:
            acc = instagram.account(token)
            kind = "süresiz sistem kullanıcısı anahtarı" if instagram.is_system_user_token(token) else "Instagram girişi anahtarı"
            print(f"[check] Instagram OK: @{acc['username']} (kimlik {acc['user_id']}, {kind})")
            try:
                st = instagram.profile_stats(token, acc["user_id"])
                print(f"[check] Takipçi: {st.get('followers_count', '?')}, paylaşım: {st.get('media_count', '?')}")
            except Exception as exc:
                print(f"[check] Takipçi sayısı okunamadı: {exc}")
            refusal = instagram.trial_reels_check(token, acc["user_id"])
            print("[check] Deneme Reels: hesap uygun" if not refusal else f"[check] Deneme Reels: kabul edilmiyor ({refusal})")
        except Exception as exc:
            ok = False
            print(f"[check] Instagram HATA: {exc}")
        if instagram.is_system_user_token(token):
            try:
                granted = instagram.granted_permissions(token)
                print(f"[check] İzinler: {', '.join(granted) or '-'}")
                if "instagram_content_publish" not in granted:
                    ok = False
                    print("[check] Instagram HATA: anahtarda instagram_content_publish (paylaşım) izni yok")
            except Exception as exc:
                print(f"[check] İzinler okunamadı: {exc}")
    from .config import GEMINI_MODEL, MODEL, PROVIDER
    key_name, model = ("ANTHROPIC_API_KEY", MODEL) if PROVIDER == "claude" else ("GEMINI_API_KEY", GEMINI_MODEL)
    if os.environ.get(key_name):
        try:
            from .write import provider
            print(f"[check] Yapay zekâ OK: {PROVIDER} / {provider().check()}")
        except Exception as exc:
            ok = False
            print(f"[check] Yapay zekâ HATA ({PROVIDER} / {model}): {exc}")
    else:  # not an error yet: the key may simply not be added
        print(f"[check] Yapay zekâ UYARI: {key_name} henüz eklenmedi ({PROVIDER} seçili)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
