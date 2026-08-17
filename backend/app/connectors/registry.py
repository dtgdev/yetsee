from app.connectors.news_rss import GoogleNewsConnector
from app.connectors.hacker_news import HackerNewsConnector


def live_connectors():
    return [GoogleNewsConnector(), HackerNewsConnector()]
