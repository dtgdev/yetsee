from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
import httpx
from app.connectors.base import Observation


class GoogleNewsConnector:
    name = "google_news"
    url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

    async def fetch(self) -> list[Observation]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(self.url, headers={"User-Agent": "YetSee/1.1"})
            response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        observations: list[Observation] = []
        for item in root.findall("./channel/item")[:40]:
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            published = item.findtext("pubDate")
            published_at: datetime | None = None
            if published:
                try:
                    published_at = parsedate_to_datetime(published).replace(tzinfo=None)
                except (TypeError, ValueError):
                    pass
            if title and url:
                observations.append(Observation(self.name, title, url, published_at=published_at))
        return observations
