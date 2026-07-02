#!/usr/bin/env python3
"""Phase 0 spike: verify Composio session search + execute for Digital Worker."""
from __future__ import annotations

import json
import sys

from aunix.composio.normalize import normalize_rows
from aunix.composio.operations import execute_tool, list_toolkit_connections, search_tools


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "list hubspot deals"
    print("== Connections ==")
    print(json.dumps(list_toolkit_connections(), indent=2, default=str))
    print("\n== Search ==")
    search = search_tools(query)
    print(json.dumps(search, indent=2, default=str)[:4000])
    slug = None
    if isinstance(search, dict):
        for key in ("tools", "results", "data"):
            items = search.get(key)
            if isinstance(items, list) and items:
                first = items[0]
                if isinstance(first, dict):
                    slug = first.get("slug") or first.get("tool_slug") or first.get("name")
                else:
                    slug = getattr(first, "slug", None) or getattr(first, "tool_slug", None)
                break
    if not slug:
        print("\nNo tool slug found in search results; pass a slug manually as argv[2].")
        return 1
    if len(sys.argv) > 2:
        slug = sys.argv[2]
    print(f"\n== Execute {slug} ==")
    raw = execute_tool(slug, {})
    rows = normalize_rows(raw)
    print(json.dumps({"row_count": len(rows), "sample": rows[:3], "raw_preview": str(raw)[:2000]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
