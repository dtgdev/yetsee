import asyncio
import httpx
from app.connectors.base import Observation


class HackerNewsConnector:
    name = "hacker_news"
    base = "https://hacker-news.firebaseio.com/v0"

    async def fetch(self) -> list[Observation]:
        async with httpx.AsyncClient(timeout=15) as client:
            ids = (await client.get(f"{self.base}/topstories.json")).json()[:30]

            async def one(story_id: int):
                try:
                    r = await client.get(f"{self.base}/item/{story_id}.json")
                    item = r.json() or {}
                    title = item.get("title")
                    if not title:
                        return None
                    return Observation(
                        self.name,
                        title,
                        item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                        metadata={"story_id": story_id, "score": item.get("score", 0)},
                    )
                except Exception:
                    return None

            rows = await asyncio.gather(*(one(i) for i in ids))
        return [x for x in rows if x]
