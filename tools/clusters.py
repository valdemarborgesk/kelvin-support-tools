#!/usr/bin/env python3
"""Kelvin cluster and node info via REST API.

Usage:
    python tools/clusters.py --env beta list [--search <term>]
    python tools/clusters.py --env beta get <name>
    python tools/clusters.py --env beta nodes <cluster-name>
"""

import argparse
import json
import sys

from api_client import add_common_args, get_client, format_table


def cmd_list(args):
    client = get_client(args)
    params = {}
    if args.search:
        params["search"] = args.search
    items = client.list_all("orchestration/clusters/list", params=params)
    rows = [
        {
            "name": c.get("name", ""),
            "status": c.get("status", ""),
            "type": c.get("type", ""),
            "version": c.get("kelvin_version", ""),
        }
        for c in items
    ]
    print(format_table(rows, ["name", "status", "type", "version"]))


def cmd_get(args):
    client = get_client(args)
    data = client.get(f"orchestration/clusters/{args.name}/get")
    print(json.dumps(data, indent=2))


def cmd_nodes(args):
    client = get_client(args)
    items = client.list_all(f"orchestration/clusters/{args.cluster}/nodes/list")
    rows = [
        {
            "name": n.get("name", ""),
            "status": n.get("status", ""),
            "role": n.get("role", ""),
        }
        for n in items
    ]
    print(format_table(rows, ["name", "status", "role"]))


def main():
    parser = argparse.ArgumentParser(description="Kelvin cluster and node info")
    add_common_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List clusters")
    p.add_argument("--search", help="Search term")

    # get
    p = sub.add_parser("get", help="Get cluster details")
    p.add_argument("name", help="Cluster name")

    # nodes
    p = sub.add_parser("nodes", help="List nodes in a cluster")
    p.add_argument("cluster", help="Cluster name")

    args = parser.parse_args()
    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "nodes": cmd_nodes,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
