from typing import Any

import ddgs
import ddgs.exceptions
from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool


@tool(
    "search_news",
    "Find news articles related to the provided topic and give their title, brief description, and url to Claude",
    {"query": str, "max_results": int},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_news(args: dict[str, Any]) -> dict[str, Any]:
    try:
        searcher = ddgs.DDGS()
        results = searcher.news(
            query=args["query"], max_results=args["max_results"], region="wt-wt"
        )
        return {"content": [{"type": "text", "text": results}]}
    except ddgs.exceptions.DDGSException:
        return {
            "content": [{"type": "text", "text": f"No news articles found on {args['query']}"}],
            "is_error": True
        }


@tool(
    "search_website",
    "Find sites and content within the specified website and give their title, brief description, and url to Claude",
    {"site": str, "query": str, "max_results": int},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_website(args: dict[str, Any]) -> dict[str, Any]:
    try:
        searcher = ddgs.DDGS()
        results = searcher.text(
            query=f"site:{args['site']} {args['query']}",
            max_results=args["max_results"],
            region="wt-wt",
        )
        return {"content": [{"type": "text", "text": results}]}
    except ddgs.exceptions.DDGSException:
        return {
            "content": [{"type": "text", "text": f"No websites found from {args['site']} on {args['query']}"}],
            "is_error": True
        }


search_server = create_sdk_mcp_server(
    name="search",
    version="1.0.0",
    tools=[search_news, search_website],
)
