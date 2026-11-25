#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only Nasdaq Composite *candidate* universe audit.

IMPORTANT:
- Nasdaq Trader listing directories are NOT an official COMP constituent feed.
- This audit does NOT create Nasdaq Composite breadth indicators and is NEVER
  included in the published @us-market output.
- The upstream PIT archive proves directory records only from its stated floor.
- No present-day survivors are projected backward before the archive boundary.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://github.com/TylerJForstrom/Stock-Data"
BASE = "https://raw.githubusercontent.com/TylerJForstrom/Stock-Data/main/data/symbols/pit/"
MANIFEST = "manifest.json"
DATA_FILE = "nasdaqlisted.jsonl"
USER_AGENT = "us-market-breadth-research/1.0 (point-in-time audit)"
MAX_BYTES = 5_000_000
CLEAR_TYPES = re.compile(
    r"\b(common stock|common shares?|common\b|ordinary shares?|"
    r"american depositary|american depository|"
    r"depositary shares representing common|adrs?\b|adss?\b|"
    r"limited partnership interests?|limited partner interests?|"
    r"beneficial interests?|registered shares?|new york registry shares?|"
    r"subordinate voting shares?|non.voting shares?|class [a-z] voting shares?|"
    r"class [a-z] ord shares?|ord shares?|capital stock|class [a-z] shares?)\b", re.I
)
INELIGIBLE_TYPES = re.compile(
    r"\b(warrants?|subscription rights?|rights?|preferred|"
    r"senior notes?|subordinated notes?|notes?|debentures?|"
    r"convertible securities|exchange.traded funds?|closed.end funds?|"
    r"preference shares?|units?|etns?|subscription receipts?)\b", re.I
)


class AuditError(RuntimeError):
    pass


def download(filename: str) -> bytes:
    request = Request(BASE + filename, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        data = response.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise AuditError("Source absent or exceeds safety size: " + filename)
    return data


def verified_source():
    meta = json.loads(download(MANIFEST))
    if meta.get("schema_version") != "1.0":
        raise AuditError("Unexpected PIT manifest schema")
    floor = meta.get("reconstructable_from_by_source", {}).get("nasdaqlisted")
    if not floor:
        raise AuditError("Missing per-source PIT archive boundary")
    dt.date.fromisoformat(floor)
    file_meta = next((x for x in meta.get("files", []) if x.get("name") == DATA_FILE), None)
    if not file_meta:
        raise AuditError("Manifest does not list the Nasdaq directory archive")
    payload = download(DATA_FILE)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != file_meta.get("sha256"):
        raise AuditError("Archive changed during retrieval or checksum incorrect")
    rows = []
    for line_number, line in enumerate(payload.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            ticker = row["ticker"].strip().upper()
            start = dt.date.fromisoformat(row["valid_from"])
            end = dt.date.fromisoformat(row["valid_to"]) if row.get("valid_to") else None
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise AuditError(f"Bad interval record at line {line_number}: {exc}") from exc
        if not ticker or start < dt.date.fromisoformat(floor) or (end and end <= start):
            raise AuditError(f"Invalid ticker/interval at line {line_number}")
        if row.get("etf") not in ("Y", "N") or row.get("test_issue") not in ("Y", "N"):
            raise AuditError(f"Unknown ETF or test issue flag at line {line_number}")
        rows.append((ticker, start, end, row))
    if len(rows) != file_meta.get("rows"):
        raise AuditError("Manifest row count does not match source")
    return meta, digest, rows, dt.date.fromisoformat(floor)


def load_calendar(path: Path, asof: str | None):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        dates = [dt.date.fromisoformat(r["date"]) for r in csv.DictReader(stream)]
    if len(set(dates)) != len(dates) or sorted(dates) != dates or len(dates) < 60:
        raise AuditError("Calendar must contain 60+ unique, increasing market sessions")
    if asof:
        target = dt.date.fromisoformat(asof)
        dates = [d for d in dates if d <= target]
        if not dates or dates[-1] != target:
            raise AuditError("Requested date is not in actual SP500 trading calendar")
    return dates[-60:]


def classification(row):
    if row["test_issue"] == "Y":
        return "EXCLUDED_TEST"
    if row["etf"] == "Y":
        return "EXCLUDED_ETF"
    name = str(row.get("name") or "")
    # Nasdaq Trader normally appends the security type after the first " - ".
    # Check the security description, not the issuer's legal name: an issuer
    # name containing "Rights" or "Unit" must not determine instrument type.
    security_description = name.split(" - ", 1)[-1]
    # COMP methodology explicitly allows UNITS OF BENEFICIAL INTEREST, not
    # generic SPAC units. Preserve this narrow exception (unless another
    # ineligible instrument word appears in the description).
    if re.search(r"\bunits? of beneficial interests?\b", security_description, re.I):
        if not re.search(r"\b(preferred|preference|warrants?|rights?|notes?)\b",
                         security_description, re.I):
            return "LIKELY_ELIGIBLE_TYPE"
    if INELIGIBLE_TYPES.search(security_description):
        return "EXCLUDED_SECURITY_TYPE"
    if CLEAR_TYPES.search(security_description):
        return "LIKELY_ELIGIBLE_TYPE"
    # E.g. SPAC units, trusts or abbreviated descriptions need real checking.
    return "UNRESOLVED_TYPE"


def audit(calendar, rows, floor, meta, digest):
    if calendar[0] < floor:
        raise AuditError(f"PIT history starts {floor}; cannot backfill {calendar[0]}")
    source_day = dt.datetime.fromisoformat(meta["generated_at_utc"].replace("Z", "+00:00")).date()
    if source_day < calendar[-1]:
        raise AuditError("Source archive predates requested end-of-day session")
    result = []
    previous = None
    for day in calendar:
        active = {}
        for ticker, start, end, record in rows:
            if start <= day and (end is None or day < end):
                if ticker in active:
                    raise AuditError(f"Overlapping historical intervals for {ticker} on {day}")
                active[ticker] = record
        if not 1500 <= len(active) <= 8000:
            raise AuditError(f"Suspicious Nasdaq directory count {len(active)} on {day}")
        counts = Counter(classification(rec) for rec in active.values())
        current = set(active)
        result.append({
            "date": day.isoformat(),
            "nasdaq_directory_total": len(active),
            "likely_eligible_security_type": counts["LIKELY_ELIGIBLE_TYPE"],
            "unresolved_security_type": counts["UNRESOLVED_TYPE"],
            "excluded_etf": counts["EXCLUDED_ETF"],
            "excluded_test": counts["EXCLUDED_TEST"],
            "excluded_security_type": counts["EXCLUDED_SECURITY_TYPE"],
            "new_directory_symbols": len(current - previous) if previous is not None else None,
            "removed_directory_symbols": len(previous - current) if previous is not None else None,
        })
        if sum(counts.values()) != len(active):
            raise AuditError("Classification reconciliation failed")
        previous = current
    return {
        "market": "NASDAQ_LISTING_DIRECTORY_ONLY_NOT_COMPOSITE",
        "status": "RESEARCH_CANDIDATES_NOT_OFFICIAL_INDEX_MEMBERSHIP",
        "eligible_for_us_market_publication": False,
        "source": SOURCE,
        "price_source": None,
        "asof_actual": calendar[-1].isoformat(),
        "first_session": calendar[0].isoformat(),
        "sessions": 60,
        "pit_floor": floor.isoformat(),
        "source_generated_at_utc": meta["generated_at_utc"],
        "source_sha256": digest,
        "source_intervals": len(rows),
        "method": "PIT Nasdaq listing directory, ETF/test/security-type screens; no official COMP validation",
        "limitation": "Cannot substitute listing directory for actual Nasdaq Composite index membership; no A/D, MA or 52-week metrics calculated.",
        "daily": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar", type=Path, default=Path("public/sp500_pit_daily.csv"))
    parser.add_argument("--asof", default=None)
    parser.add_argument("--outdir", type=Path, default=Path("research/nasdaq_comp"))
    args = parser.parse_args()
    dates = load_calendar(args.calendar, args.asof)
    meta, digest, rows, floor = verified_source()
    report = audit(dates, rows, floor, meta, digest)
    args.outdir.mkdir(parents=True, exist_ok=True)
    output = args.outdir / "candidate_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Nasdaq Composite: Research-only candidate universe",
        "",
        "**NOT validated COMP constituents; NOT usable in @us-market V2.0 breadth.**",
        "",
        f"- Actual trading day: {report['asof_actual']}",
        f"- Source archive begins: {report['pit_floor']}",
        f"- Historical sessions inspected: {report['sessions']}",
        f"- Nasdaq-listed securities on last day: {report['daily'][-1]['nasdaq_directory_total']}",
        f"- Likely eligible security types: {report['daily'][-1]['likely_eligible_security_type']}",
        f"- Needs manual index/type verification: {report['daily'][-1]['unresolved_security_type']}",
        "- Prices and genuine COMP constituent membership: NOT YET VERIFIED.",
        "",
        "Source: " + SOURCE,
    ]
    (args.outdir / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("RESEARCH_ONLY", report["asof_actual"], report["status"])
    print(json.dumps(report["daily"][-1], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
