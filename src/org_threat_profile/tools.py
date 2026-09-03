from typing import Any

import ddgs
from claude_agent_sdk import create_sdk_mcp_server, tool


@tool(
    "search_news",
    "Find news articles related to the provided topic and give their title, brief description, and url to Claude",
    {"query": str, "max_results": int},
)
async def search_news(args: dict[str, Any]) -> dict[str, Any]:
    searcher = ddgs.DDGS()
    results = searcher.news(
        query=args["query"], max_results=args["max_results"], region="wt-wt"
    )
    return {"content": [{"type": "text", "text": results}]}


@tool(
    "search_website",
    "Find sites and content within the specified website and give their title, brief description, and url to Claude",
    {"site": str, "query": str, "max_results": int},
)
async def search_website(args: dict[str, Any]) -> dict[str, Any]:
    searcher = ddgs.DDGS()
    results = searcher.news(
        query=f"site:{args['site']} {args['query']}",
        max_results=args["max_results"],
        region="wt-wt",
    )
    return {"content": [{"type": "text", "text": results}]}


search_server = create_sdk_mcp_server(
    name="search",
    version="1.0.0",
    tools=[search_news, search_website],
)
