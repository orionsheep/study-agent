import httpx
import asyncio

async def test():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/"
    }
    async with httpx.AsyncClient() as client:
        # Get cookie first
        await client.get("https://bilibili.com", headers=headers)
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=大学物理"
        res = await client.get(url, headers=headers)
        print(res.status_code)
        print(res.text[:200])

asyncio.run(test())
