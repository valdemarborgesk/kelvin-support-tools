#!/usr/bin/env python3
"""Kelvin data stream management via REST API.

Usage:
    python tools/datastreams.py --env beta list [--asset <name>] [--search <term>]
    python tools/datastreams.py --env beta get <name>
    python tools/datastreams.py --env beta create --name <n> --title <t> --data-type <type>
    python tools/datastreams.py --env beta delete <name>
"""

import argparse
import json
import sys

from api_client import add_common_args, get_client, format_table


def cmd_list(args):
    client = get_client(args)
    body = {}
    if args.asset:
        body["names"] = [args.asset]
    if args.search:
        body["search"] = [args.search]
    items = client.list_all_post("datastreams/list", body=body)
    rows = [
        {
            "name": ds.get("name", ""),
            "title": ds.get("title", ""),
            "data_type": ds.get("data_type", ""),
            "semantic_type": ds.get("semantic_type", ""),
            "unit": ds.get("unit", ""),
        }
        for ds in items
    ]
    print(format_table(rows, ["name", "title", "data_type", "semantic_type", "unit"]))


def cmd_get(args):
    client = get_client(args)
    data = client.get(f"datastreams/{args.name}/get")
    print(json.dumps(data, indent=2))


def cmd_create(args):
    client = get_client(args)
    body = {
        "name": args.name,
        "title": args.title,
        "data_type": args.data_type,
    }
    if args.semantic_type:
        body["semantic_type"] = args.semantic_type
    if args.unit:
        body["unit"] = args.unit
    if args.asset:
        body["asset_name"] = args.asset
    result = client.post("datastreams/create", json_data=body)
    print(f"Created data stream: {result.get('name', args.name)}")
    print(json.dumps(result, indent=2))


def cmd_delete(args):
    client = get_client(args)
    client.post(f"datastreams/{args.name}/delete")
    print(f"Deleted data stream: {args.name}")


def main():
    parser = argparse.ArgumentParser(description="Kelvin data stream management")
    add_common_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List data streams")
    p.add_argument("--asset", help="Filter by asset name")
    p.add_argument("--search", help="Search term")

    # get
    p = sub.add_parser("get", help="Get data stream details")
    p.add_argument("name", help="Data stream name")

    # create
    p = sub.add_parser("create", help="Create a data stream")
    p.add_argument("--name", required=True, help="Data stream name")
    p.add_argument("--title", required=True, help="Display title")
    p.add_argument("--data-type", required=True, choices=["boolean", "number", "string", "object"],
                    help="Data type")
    p.add_argument("--semantic-type", choices=["measurement", "computed", "set_point", "data_quality"],
                    help="Semantic type")
    p.add_argument("--unit", help="Unit of measurement")
    p.add_argument("--asset", help="Asset name to associate with")

    # delete
    p = sub.add_parser("delete", help="Delete a data stream")
    p.add_argument("name", help="Data stream name")

    args = parser.parse_args()
    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "create": cmd_create,
        "delete": cmd_delete,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
