#!/usr/bin/env python3
"""Kelvin asset and asset-type management via REST API.

Usage:
    python tools/assets.py --env beta list [--type <asset-type>] [--search <term>]
    python tools/assets.py --env beta get <name>
    python tools/assets.py --env beta create --name <n> --title <t> --asset-type <at>
    python tools/assets.py --env beta delete <name>
    python tools/assets.py --env beta list-types
    python tools/assets.py --env beta create-type --name <n> --title <t>
    python tools/assets.py --env beta delete-type <name>
"""

import argparse
import json
import sys

from api_client import add_common_args, get_client, format_table


def cmd_list(args):
    client = get_client(args)
    params = {}
    if args.type:
        params["asset_type_names"] = args.type
    if args.search:
        params["search"] = args.search
    items = client.list_all("assets/list", params=params)
    rows = [
        {
            "name": a.get("name", ""),
            "title": a.get("title", ""),
            "asset_type": a.get("asset_type_name", ""),
            "status": a.get("status", ""),
        }
        for a in items
    ]
    print(format_table(rows, ["name", "title", "asset_type", "status"]))


def cmd_get(args):
    client = get_client(args)
    data = client.get(f"assets/{args.name}/get")
    print(json.dumps(data, indent=2))


def cmd_create(args):
    client = get_client(args)
    body = {"name": args.name, "title": args.title, "asset_type_name": args.asset_type}
    if args.properties:
        body["properties"] = json.loads(args.properties)
    result = client.post("assets/create", json_data=body)
    print(f"Created asset: {result.get('name', args.name)}")
    print(json.dumps(result, indent=2))


def cmd_delete(args):
    client = get_client(args)
    client.post(f"assets/{args.name}/delete")
    print(f"Deleted asset: {args.name}")


def cmd_list_types(args):
    client = get_client(args)
    items = client.list_all("assets/types/list")
    rows = [
        {
            "name": t.get("name", ""),
            "title": t.get("title", ""),
        }
        for t in items
    ]
    print(format_table(rows, ["name", "title"]))


def cmd_create_type(args):
    client = get_client(args)
    body = {"name": args.name, "title": args.title}
    if args.description:
        body["description"] = args.description
    result = client.post("assets/types/create", json_data=body)
    print(f"Created asset type: {result.get('name', args.name)}")
    print(json.dumps(result, indent=2))


def cmd_delete_type(args):
    client = get_client(args)
    client.post(f"assets/types/{args.name}/delete")
    print(f"Deleted asset type: {args.name}")


def main():
    parser = argparse.ArgumentParser(description="Kelvin asset management")
    add_common_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List assets")
    p.add_argument("--type", help="Filter by asset type name")
    p.add_argument("--search", help="Search term")

    # get
    p = sub.add_parser("get", help="Get asset details")
    p.add_argument("name", help="Asset name")

    # create
    p = sub.add_parser("create", help="Create an asset")
    p.add_argument("--name", required=True, help="Asset name")
    p.add_argument("--title", required=True, help="Display title")
    p.add_argument("--asset-type", required=True, help="Asset type name")
    p.add_argument("--properties", help="JSON string of custom properties")

    # delete
    p = sub.add_parser("delete", help="Delete an asset")
    p.add_argument("name", help="Asset name")

    # list-types
    sub.add_parser("list-types", help="List asset types")

    # create-type
    p = sub.add_parser("create-type", help="Create an asset type")
    p.add_argument("--name", required=True, help="Type name")
    p.add_argument("--title", required=True, help="Display title")
    p.add_argument("--description", help="Description")

    # delete-type
    p = sub.add_parser("delete-type", help="Delete an asset type")
    p.add_argument("name", help="Type name")

    args = parser.parse_args()
    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "create": cmd_create,
        "delete": cmd_delete,
        "list-types": cmd_list_types,
        "create-type": cmd_create_type,
        "delete-type": cmd_delete_type,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
