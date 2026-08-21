from app.scientific_literature.pubmed import PubMedClient, parse_pubmed_xml

SAMPLE = b'''<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345678</PMID><Article><Journal><JournalIssue><PubDate><Year>2024</Year><Month>Mar</Month><Day>12</Day></PubDate></JournalIssue><Title>Journal of Precision Oncology</Title></Journal><ArticleTitle>MET amplification and acquired osimertinib resistance</ArticleTitle><Abstract><AbstractText Label="BACKGROUND" NlmCategory="BACKGROUND">Osimertinib is used in EGFR-mutant lung cancer.</AbstractText><AbstractText Label="RESULTS" NlmCategory="RESULTS">MET amplification was observed after acquired resistance.</AbstractText></Abstract><AuthorList><Author><LastName>Example</LastName><ForeName>Ada</ForeName><Initials>A</Initials></Author></AuthorList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="pubmed">12345678</ArticleId><ArticleId IdType="doi">10.1000/example.1</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>'''


def test_parse_pubmed_xml_preserves_source_identity_and_abstract_locators():
    article = parse_pubmed_xml(SAMPLE, requested_pmid="12345678")

    assert article.pmid == "12345678"
    assert article.doi == "10.1000/example.1"
    assert article.title == "MET amplification and acquired osimertinib resistance"
    assert article.journal == "Journal of Precision Oncology"
    assert article.publication_date.isoformat() == "2024-03-12"
    assert article.authors[0]["last_name"] == "Example"
    assert [section["locator"] for section in article.abstract_sections] == ["abstract:1", "abstract:2"]
    assert article.abstract_sections[1]["label"] == "RESULTS"
    assert len(article.raw_xml_hash) == 64


def test_pubmed_client_validates_requested_identity():
    client = PubMedClient(fetcher=lambda _url: SAMPLE)
    article = client.fetch_article("12345678")
    assert article.source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


def test_pubmed_client_rejects_non_numeric_pmid():
    client = PubMedClient(fetcher=lambda _url: SAMPLE)
    try:
        client.fetch_article("not-a-pmid")
    except ValueError as exc:
        assert "digits only" in str(exc)
    else:
        raise AssertionError("Expected invalid PMID to be rejected")


def test_parser_rejects_mismatched_pubmed_identity():
    try:
        parse_pubmed_xml(SAMPLE, requested_pmid="99999999")
    except ValueError as exc:
        assert "returned PMID" in str(exc)
    else:
        raise AssertionError("Expected mismatched PMID to be rejected")
