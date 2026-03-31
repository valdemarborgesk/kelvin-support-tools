#!/usr/bin/env python3
"""Kelvin timeseries data queries via REST API.

Usage:
    python tools/timeseries.py --env beta latest --asset pump-01 --datastream pressure
    python tools/timeseries.py --env beta query --asset pump-01 --datastream pressure [--start 2h] [--end now]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from api_client import add_common_args, get_client, format_table


def parse_relative_time(value: str) -> str:
    """Parse relative time like '1h', '24h', '30m', '7d' to ISO8601."""
    now = datetime.now(timezone.utc)
    if value == "now":
        return now.isoformat()

    try:
        # Try ISO8601 first
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError:
        pass

    unit = value[-1]
    amount = int(value[:-1])
    deltas = {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}
    if unit not in deltas:
        print(f"ERROR: Invalid time format '{value}'. Use: 30m, 1h, 24h, 7d, or ISO8601", file=sys.stderr)
        sys.exit(1)
    return (now - deltas[unit]).isoformat()


def cmd_latest(args):
    client = get_client(args)
    body = {
        "selectors": [{"asset": args.asset, "data_stream": args.datastream}],
    }
    data = client.post("timeseries/last/get", json_data=body)
    results = data if isinstance(data, list) else data.get("data", [])
    if not results:
        print(f"No data found for asset={args.asset} datastream={args.datastream}")
        return

    for entry in results:
        ts = entry.get("timestamp", "?")
        val = entry.get("value", "?")
        quality = entry.get("quality", "?")
        print(f"Asset:      {entry.get('asset', args.asset)}")
        print(f"Datastream: {entry.get('data_stream', args.datastream)}")
        print(f"Timestamp:  {ts}")
        print(f"Value:      {val}")
        print(f"Quality:    {quality}")


def cmd_query(args):
    client = get_client(args)
    start = parse_relative_time(args.start)
    end = parse_relative_time(args.end)

    body = {
        "selectors": [{"asset": args.asset, "data_stream": args.datastream}],
        "start_time": start,
        "end_time": end,
    }
    if args.agg and args.agg != "none":
        body["agg"] = args.agg

    data = client.post("timeseries/range/get", json_data=body)
    results = data if isinstance(data, list) else data.get("data", [])
    if not results:
        print(f"No data in range {start} to {end} for asset={args.asset} datastream={args.datastream}")
        return

    rows = [
        {
            "timestamp": r.get("timestamp", ""),
            "value": str(r.get("value", "")),
            "quality": str(r.get("quality", "")),
        }
        for r in results
    ]
    print(f"Asset: {args.asset} | Datastream: {args.datastream}")
    print(f"Range: {start} to {end}")
    print()
    print(format_table(rows, ["timestamp", "value", "quality"]))


def main():
    parser = argparse.ArgumentParser(description="Kelvin timeseries data queries")
    add_common_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    # latest
    p = sub.add_parser("latest", help="Get latest data point")
    p.add_argument("--asset", required=True, help="Asset name")
    p.add_argument("--datastream", required=True, help="Data stream name")

    # query
    p = sub.add_parser("query", help="Query timeseries range")
    p.add_argument("--asset", required=True, help="Asset name")
    p.add_argument("--datastream", required=True, help="Data stream name")
    p.add_argument("--start", default="1h", help="Start time (1h, 24h, 7d, or ISO8601). Default: 1h")
    p.add_argument("--end", default="now", help="End time. Default: now")
    p.add_argument("--agg", choices=["none", "mean", "min", "max", "count", "sum"],
                    default="none", help="Aggregation. Default: none")

    args = parser.parse_args()
    commands = {
        "latest": cmd_latest,
        "query": cmd_query,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
