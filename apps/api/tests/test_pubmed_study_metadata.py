from app.scientific_literature.pubmed import parse_pubmed_xml


def test_parse_pubmed_xml_preserves_structured_study_metadata():
    xml = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345678</PMID><Article><ArticleTitle>Randomized phase 3 study NCT02151981</ArticleTitle><Journal><Title>Example Journal</Title><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue></Journal><Language>eng</Language><Abstract><AbstractText Label="METHODS">Patients entered NCT02151981, a randomized phase 3 study.</AbstractText></Abstract><PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType><PublicationType>Clinical Trial, Phase III</PublicationType></PublicationTypeList></Article><MeshHeadingList><MeshHeading><DescriptorName>Carcinoma, Non-Small-Cell Lung</DescriptorName></MeshHeading><MeshHeading><DescriptorName>Osimertinib</DescriptorName></MeshHeading></MeshHeadingList></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>'''
    article = parse_pubmed_xml(xml, requested_pmid="12345678")
    assert article.publication_types == ["Randomized Controlled Trial", "Clinical Trial, Phase III"]
    assert article.mesh_terms == ["Carcinoma, Non-Small-Cell Lung", "Osimertinib"]
    assert article.trial_identifiers == ["NCT02151981"]
    assert article.languages == ["eng"]


def test_trial_identifiers_are_deduplicated_and_only_explicit_nct_ids_are_used():
    xml = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345679</PMID><Article><ArticleTitle>Study NCT02296125</ArticleTitle><Journal><Title>Example</Title><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue></Journal><Abstract><AbstractText>NCT02296125 enrolled patients; subgroup n = 17.</AbstractText></Abstract><DataBankList><DataBank><AccessionNumberList><AccessionNumber>NCT02296125</AccessionNumber></AccessionNumberList></DataBank></DataBankList></Article></MedlineCitation><PubmedData><ArticleIdList /></PubmedData></PubmedArticle></PubmedArticleSet>'''
    article = parse_pubmed_xml(xml)
    assert article.trial_identifiers == ["NCT02296125"]
