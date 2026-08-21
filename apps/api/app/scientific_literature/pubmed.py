from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scientific_literature import ScientificPassage, ScientificPublication

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = "".join(node.itertext()).strip()
    return " ".join(value.split()) or None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _publication_date(article: ET.Element) -> date | None:
    pub_date = article.find(".//JournalIssue/PubDate")
    if pub_date is None:
        return None
    year = _text(pub_date.find("Year"))
    month = _text(pub_date.find("Month"))
    day = _text(pub_date.find("Day"))
    if not year or not year.isdigit():
        medline = _text(pub_date.find("MedlineDate"))
        if medline and len(medline) >= 4 and medline[:4].isdigit():
            year = medline[:4]
        else:
            return None
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    month_number = int(month) if month and month.isdigit() else months.get((month or "").lower()[:3], 1)
    day_number = int(day) if day and day.isdigit() else 1
    try:
        return date(int(year), month_number, day_number)
    except ValueError:
        return date(int(year), 1, 1)


@dataclass(frozen=True)
class PubMedArticle:
    pmid: str
    doi: str | None
    title: str
    journal: str | None
    publication_date: date | None
    authors: list[dict[str, str]]
    abstract_sections: list[dict[str, str | None]]
    source_url: str
    raw_xml_hash: str


class PubMedClient:
    def __init__(self, fetcher: Callable[[str], bytes] | None = None) -> None:
        self._fetcher = fetcher or self._fetch

    @staticmethod
    def _fetch(url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "YetSee/0.9 scientific-literature"})
        with urlopen(request, timeout=20) as response:
            return response.read()

    def fetch_article(self, pmid: str) -> PubMedArticle:
        clean_pmid = pmid.strip()
        if not clean_pmid.isdigit():
            raise ValueError("PMID must contain digits only")
        url = f"{EUTILS_BASE}?{urlencode({'db':'pubmed','id':clean_pmid,'retmode':'xml'})}"
        return parse_pubmed_xml(self._fetcher(url), requested_pmid=clean_pmid)


def parse_pubmed_xml(xml_bytes: bytes, requested_pmid: str | None = None) -> PubMedArticle:
    root = ET.fromstring(xml_bytes)
    article = root.find(".//PubmedArticle")
    if article is None:
        raise ValueError("PubMed response did not contain a PubmedArticle")
    pmid = _text(article.find(".//MedlineCitation/PMID"))
    if not pmid:
        raise ValueError("PubMed article is missing PMID")
    if requested_pmid and pmid != requested_pmid:
        raise ValueError(f"PubMed returned PMID {pmid} for requested PMID {requested_pmid}")
    title = _text(article.find(".//Article/ArticleTitle"))
    if not title:
        raise ValueError("PubMed article is missing title")
    doi = None
    for identifier in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if identifier.attrib.get("IdType") == "doi":
            doi = _text(identifier)
            break
    authors: list[dict[str, str]] = []
    for author in article.findall(".//Article/AuthorList/Author"):
        item = {key: value for key, value in {
            "last_name": _text(author.find("LastName")),
            "fore_name": _text(author.find("ForeName")),
            "initials": _text(author.find("Initials")),
            "collective_name": _text(author.find("CollectiveName")),
        }.items() if value}
        if item:
            authors.append(item)
    sections: list[dict[str, str | None]] = []
    for index, abstract in enumerate(article.findall(".//Article/Abstract/AbstractText"), start=1):
        text = _text(abstract)
        if text:
            sections.append({"label": abstract.attrib.get("Label"), "nlm_category": abstract.attrib.get("NlmCategory"), "text": text, "locator": f"abstract:{index}"})
    return PubMedArticle(
        pmid=pmid,
        doi=doi,
        title=title,
        journal=_text(article.find(".//Article/Journal/Title")),
        publication_date=_publication_date(article),
        authors=authors,
        abstract_sections=sections,
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        raw_xml_hash=_sha256(xml_bytes.decode("utf-8")),
    )


def ingest_pubmed_article(db: Session, pmid: str, client: PubMedClient | None = None) -> tuple[ScientificPublication, list[ScientificPassage], bool]:
    article = (client or PubMedClient()).fetch_article(pmid)
    existing = db.scalar(select(ScientificPublication).where(ScientificPublication.source_system == "pubmed", ScientificPublication.source_id == article.pmid))
    if existing is not None:
        passages = list(db.scalars(select(ScientificPassage).where(ScientificPassage.publication_id == existing.id)).all())
        return existing, passages, False
    canonical = json.dumps({"pmid":article.pmid,"doi":article.doi,"title":article.title,"journal":article.journal,"publication_date":article.publication_date.isoformat() if article.publication_date else None,"authors":article.authors,"abstract":article.abstract_sections}, sort_keys=True, ensure_ascii=False)
    publication = ScientificPublication(
        source_system="pubmed", source_id=article.pmid, pmid=article.pmid, doi=article.doi,
        title=article.title, journal=article.journal, publication_date=article.publication_date,
        authors_json=article.authors,
        metadata_json={"provider":"NCBI PubMed","raw_xml_hash":article.raw_xml_hash,"abstract_section_count":len(article.abstract_sections)},
        source_url=article.source_url, retrieval_ref=f"pubmed:pmid:{article.pmid}", content_hash=_sha256(canonical),
    )
    db.add(publication)
    db.flush()
    passages: list[ScientificPassage] = []
    for section in article.abstract_sections:
        text = str(section["text"])
        passage = ScientificPassage(
            publication_id=publication.id,
            section=section.get("label") or section.get("nlm_category") or "Abstract",
            locator=section.get("locator"), text=text, content_hash=_sha256(text),
            provenance_json={"source_system":"pubmed","pmid":article.pmid,"doi":article.doi,"source_url":article.source_url,"retrieval_ref":publication.retrieval_ref,"canonical_source":True},
        )
        db.add(passage)
        passages.append(passage)
    db.commit()
    db.refresh(publication)
    return publication, passages, True
