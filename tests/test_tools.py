import pytest

from org_threat_profile import tools


@pytest.mark.asyncio
async def test_search_news():
    result = await tools.search_news.handler({"query": "Python programming", "max_results": 3})
    assert isinstance(result.get("content"), list)
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"
    articles = result["content"][0]["text"]
    if isinstance(articles, list):
        assert len(articles) <= 3


@pytest.mark.asyncio
async def test_search_website():
    result = await tools.search_news.handler({"site": "stackoverflow.com", "query": "Python programming", "max_results": 3})
    assert isinstance(result.get("content"), list)
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"
    articles = result["content"][0]["text"]
    if isinstance(articles, list):
        assert len(articles) <= 3
