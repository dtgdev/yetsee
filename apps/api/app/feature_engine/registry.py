from app.feature_engine.extractors.semantic import SemanticFeatureExtractor
from app.feature_engine.extractors.source import SourceFeatureExtractor
from app.feature_engine.extractors.statistical import StatisticalFeatureExtractor
from app.feature_engine.extractors.temporal import TemporalFeatureExtractor


class FeatureExtractorRegistry:
    def __init__(self):
        extractors = [TemporalFeatureExtractor(), StatisticalFeatureExtractor(), SourceFeatureExtractor(), SemanticFeatureExtractor()]
        self._extractors = {extractor.manifest().id: extractor for extractor in extractors}

    def all(self):
        return list(self._extractors.values())

    def get(self, extractor_id: str):
        return self._extractors[extractor_id]


registry = FeatureExtractorRegistry()
