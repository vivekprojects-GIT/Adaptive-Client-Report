"""Create the Hugging Face Space and push this repo to it.

    python scripts/deploy_space.py --space saivivek6/adaptive-client-reporting

Requires an HF token with WRITE scope, supplied by the environment — never
typed into a chat or committed:

    setx HF_TOKEN hf_xxx          (Windows, new shell after)
    export HF_TOKEN=hf_xxx        (bash)

or run `python -m huggingface_hub.cli.hf auth login` once. (The bare `hf`
command on this machine is Higgsfield, an unrelated tool — hence the
module form.)

WHAT IS UPLOADED
----------------
Explicit deny list, not "whatever is lying around". Secrets, local
databases, build output and caches never leave the machine:

    .env  credentials.json  token.json   the actual keys
    data/                                local SQLite + generated reports
    node_modules/  dist/  __pycache__/   rebuilt in the container

Everything the Docker build needs (ape/, scripts/, frontend/ sources,
Dockerfile, requirements.txt, README.md) does go.

The Space builds from the Dockerfile: stage one compiles the React app,
stage two serves API + SPA on 7860. Configuration is entirely env vars,
so no secret is ever baked into the image.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Anything matching these never uploads. Deny-by-default on the categories
# that matter: credentials, local state, build artefacts.
IGNORE = [
    ".env", ".env.*", "credentials.json", "token.json", "*.pem", "*.key",
    "data/**", "**/__pycache__/**", "*.pyc",
    "node_modules/**", "frontend/node_modules/**", "frontend/dist/**",
    ".git/**", ".venv/**", "venv/**", "*.zip", "*.db", "*.sqlite*",
    ".pytest_cache/**", ".ruff_cache/**",
]

REQUIRED_SECRETS = [
    ("ANTHROPIC_API_KEY", "LLM writes reports and answers questions"),
    ("APE_MONGO_URI", "config store: report types, templates, audit"),
    ("APE_REPORT_TOKEN_SECRET", "signs report links and advisor sessions"),
    ("ADVISOR_PASSWORD", "gates the advisor and admin surfaces"),
    ("APP_BASE_URL", "https://<space>.hf.space — base for emailed links"),
]
OPTIONAL_SECRETS = [
    ("EMAIL_PROVIDER", "gmail — otherwise sends write .eml files"),
    ("EMAIL_FROM", "the Gmail address that granted consent"),
    ("GMAIL_TOKEN_JSON", "contents of token.json"),
    ("DATABASE_URL", "hosted Postgres, so learning survives restarts"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="owner/space-name")
    ap.add_argument("--private", action="store_true",
                    help="create private (client links still need the token)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would upload and stop")
    args = ap.parse_args()

    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    api = HfApi(token=token)

    # --dry-run inspects local files only, so it must work without a token:
    # seeing what would leave the machine should never require credentials.
    if not args.dry_run:
        try:
            who = api.whoami()
            print(f"authenticated as {who.get('name')}")
        except Exception:
            sys.exit(
                "Not authenticated.\n"
                "  set HF_TOKEN to a WRITE token from "
                "https://huggingface.co/settings/tokens\n"
                "  or run: python -m huggingface_hub.cli.hf auth login")

    if args.dry_run:
        # The same public filter upload_folder applies, so this manifest is
        # exactly what would be pushed — no private internals to drift.
        from huggingface_hub.utils import filter_repo_objects
        rel = [f.relative_to(ROOT).as_posix()
               for f in ROOT.rglob("*") if f.is_file()]
        kept = sorted(filter_repo_objects(rel, ignore_patterns=IGNORE))
        total = sum((ROOT / f).stat().st_size for f in kept)
        print(f"\n{len(kept)} files, {total / 1e6:.1f} MB would upload\n")
        for f in kept[:40]:
            print("   ", f)
        if len(kept) > 40:
            print(f"    ... and {len(kept) - 40} more")

        # Belt and braces: the ignore list is the guard, this is the alarm.
        leaked = [f for f in kept if any(
            x in f.lower() for x in ("credential", "token.json", ".env",
                                     "secret", ".db", ".pem"))]
        print("\nsecret check:",
              "CLEAN - nothing sensitive in the manifest" if not leaked
              else f"STOP - would upload {leaked}")
        return

    print(f"creating space {args.space} (docker sdk)")
    try:
        api.create_repo(repo_id=args.space, repo_type="space",
                        space_sdk="docker", private=args.private,
                        exist_ok=True)
    except HfHubHTTPError as exc:
        sys.exit(f"could not create space: {exc}")

    print("uploading (first push builds the container — a few minutes)")
    api.upload_folder(
        repo_id=args.space, repo_type="space", folder_path=str(ROOT),
        ignore_patterns=IGNORE,
        commit_message="Deploy adaptive client reporting")

    url = f"https://huggingface.co/spaces/{args.space}"
    print(f"\npushed -> {url}")
    print("\nNOW SET SECRETS (Settings -> Variables and secrets).")
    print("The build will start immediately but the app cannot run without:")
    for name, why in REQUIRED_SECRETS:
        print(f"  {name:<26} {why}")
    print("\nOptional:")
    for name, why in OPTIONAL_SECRETS:
        print(f"  {name:<26} {why}")
    print(f"\nAPP_BASE_URL should be:  {url.replace('/spaces/', '/').replace('huggingface.co/', '').replace('/', '-')}")
    print("  (or read it off the Space page once it is running)")


if __name__ == "__main__":
    main()
