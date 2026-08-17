from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request


def request(method: str, path: str) -> object:
    base = os.environ.get("YETSEE_API_URL", "http://localhost:8100/api/v1").rstrip("/")
    req = urllib.request.Request(f"{base}{path}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(prog="yetsee", description="YetSee OS Alpha CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("plugins")
    sub.add_parser("events")
    wf = sub.add_parser("run")
    wf.add_argument("workflow", nargs="?", default="intelligence-refresh")
    wf.add_argument("--hours", type=int, default=720)
    hist = sub.add_parser("history")
    hist.add_argument("investigation_id")

    investigate = sub.add_parser("investigate")
    investigate_sub = investigate.add_subparsers(dest="investigate_command", required=True)
    investigate_sub.add_parser("list")
    inv_open = investigate_sub.add_parser("open")
    inv_open.add_argument("identifier", help="Investigation UUID or slug")
    inv_promote = investigate_sub.add_parser("promote")
    inv_promote.add_argument("candidate_id")
    inv_promote.add_argument("--override", action="store_true")
    inv_promote.add_argument("--reason")
    inv_refresh = investigate_sub.add_parser("refresh")
    inv_refresh.add_argument("investigation_id")
    inv_evidence = investigate_sub.add_parser("evidence-agent")
    inv_evidence.add_argument("investigation_id")

    hypothesis = sub.add_parser("hypothesis")
    hypothesis_sub = hypothesis.add_subparsers(dest="hypothesis_command", required=True)
    h_conf = hypothesis_sub.add_parser("confidence")
    h_conf.add_argument("investigation_id")
    h_conf.add_argument("hypothesis_id")
    h_hist = hypothesis_sub.add_parser("history")
    h_hist.add_argument("investigation_id")
    h_hist.add_argument("hypothesis_id")
    h_recalc = hypothesis_sub.add_parser("recalculate")
    h_recalc.add_argument("investigation_id")
    h_recalc.add_argument("hypothesis_id")

    args = parser.parse_args()
    if args.command == "status":
        result = request("GET", "/kernel/status")
    elif args.command == "plugins":
        result = request("GET", "/plugins")
    elif args.command == "events":
        result = request("GET", "/events?limit=50")
    elif args.command == "run":
        result = request("POST", f"/workflows/{args.workflow}/run?hours={args.hours}")
    elif args.command == "history":
        result = request("GET", f"/investigations/{args.investigation_id}/history")
    elif args.command == "hypothesis":
        base = f"/investigations/{args.investigation_id}/hypotheses/{args.hypothesis_id}/confidence"
        if args.hypothesis_command == "confidence":
            result = request("GET", base)
        elif args.hypothesis_command == "history":
            result = request("GET", f"{base}/history")
        elif args.hypothesis_command == "recalculate":
            result = request("POST", f"{base}/recalculate")
        else:
            raise SystemExit(2)
    elif args.command == "investigate":
        if args.investigate_command == "list":
            result = request("GET", "/investigations")
        elif args.investigate_command == "open":
            identifier = args.identifier
            path = f"/investigations/{identifier}/workspace" if "-" in identifier and len(identifier) >= 32 else f"/investigations/by-slug/{identifier}"
            result = request("GET", path)
        elif args.investigate_command == "promote":
            from urllib.parse import urlencode
            query = {}
            if args.override:
                query["override"] = "true"
            if args.reason:
                query["reason"] = args.reason
            suffix = f"?{urlencode(query)}" if query else ""
            result = request("POST", f"/discovery/candidates/{args.candidate_id}/promote{suffix}")
        elif args.investigate_command == "refresh":
            result = request("POST", f"/investigations/{args.investigation_id}/refresh")
        elif args.investigate_command == "evidence-agent":
            result = request("POST", f"/investigations/{args.investigation_id}/agents/evidence/run")
        else:
            raise SystemExit(2)
    else:
        raise SystemExit(2)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
