from app.signal_engine.connectors.demo import DemoConnector
from app.signal_engine.connectors.hacker_news import HackerNewsConnector
from app.signal_engine.connectors.reddit import RedditConnector
from app.signal_engine.connectors.google_trends import GoogleTrendsConnector
from app.signal_engine.contracts import Connector


class ConnectorRegistry:
    def __init__(self) -> None:
        connectors: list[Connector] = [DemoConnector(), HackerNewsConnector(), RedditConnector(), GoogleTrendsConnector()]
        self._connectors = {connector.manifest().id: connector for connector in connectors}

    def all(self) -> list[Connector]:
        return list(self._connectors.values())

    def get(self, connector_id: str) -> Connector:
        if connector_id not in self._connectors:
            raise KeyError(connector_id)
        return self._connectors[connector_id]


registry = ConnectorRegistry()
