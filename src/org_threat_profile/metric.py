import glob
import re
from enum import Enum, auto
from io import BytesIO
from typing import NamedTuple
from urllib.parse import urljoin

import ddgs
import numpy as np
import pptx.shapes.autoshape
import pymupdf
import pymupdf4llm
import pytesseract
import requests
import tldextract
from bs4 import BeautifulSoup
from docx import Document as WordDocument
from markdownify import markdownify
from PIL import Image
from pptx import Presentation as PowerPointPresentation
from thefuzz import fuzz
from urlextract import URLExtract


class YamlKey:
    def __init__(self):
        self.keys = []
        self.single_indent = None

    def add_key(self, key_line: str):
        indent_match = re.match(r"^(\s+)\w", key_line)
        if indent_match:
            indent = indent_match.group(1)
            key = key_line.strip()
            if self.single_indent is None:
                self.single_indent = indent
                indent_level = 1
            else:
                indent_level = indent.count(self.single_indent)
        else:
            key = key_line
            indent_level = 0

        self.keys[indent_level:] = []
        key = key[: key.find(":")]  # RM semi-colon at the end
        self.keys.append(key)

    def __str__(self):
        return ":".join(self.keys)


class Fact(NamedTuple):
    key: str
    content: str


class Source(NamedTuple):
    title: str
    urls: list[str]


class ProcessedOutput(NamedTuple):
    stated_facts: dict[str, list[Fact]]
    inferred_facts: dict[str, list[Fact]]
    sources: dict[str, Source]


def process_output(model_output_file: str) -> ProcessedOutput:
    stated_facts = {}
    inferred_facts = {}
    used_sources = {}
    source_mode = False
    tracked_key = YamlKey()
    with open(model_output_file, "r") as f:
        for line in f:
            if not source_mode:
                if "# Source key:" in line:
                    source_mode = True
                    continue

                if re.match(r"^(\s*)\w+:", line):
                    tracked_key.add_key(line)

                if "(stated)" in line:
                    current_facts = stated_facts
                    fact_keyword = "(stated)"
                elif "(inferred)" in line:
                    current_facts = inferred_facts
                    fact_keyword = "(inferred)"
                else:
                    continue

                source_match = re.search(r"\[([^\]]+)\]", line)
                if source_match:
                    sources = source_match.group(1)
                    processed_line = line.replace(f"[{sources}]", "")
                    for source in sources.split(","):
                        source = source.strip()
                        processed_line = processed_line.replace(f" {fact_keyword}", "")
                        quoted_data = re.search(r'"([^"]*)"', processed_line)
                        if quoted_data:
                            processed_line = quoted_data.group(1)
                        processed_line = processed_line.strip()
                        fact = Fact(key=str(tracked_key), content=processed_line)
                        if current_facts.get(source) is None:
                            current_facts[source] = [fact]
                        else:
                            current_facts[source].append(fact)
            else:
                source_match = re.search(r"\[([^\]]+)\]", line)
                if source_match:
                    source = source_match.group(1)
                    title = line[line.find("]") + 1 : line.find("(")].strip()
                    urls = [
                        url.replace(")", "") for url in URLExtract().find_urls(line)
                    ]
                    used_sources[source] = Source(title=title, urls=urls)

    return ProcessedOutput(
        stated_facts=stated_facts, inferred_facts=inferred_facts, sources=used_sources
    )


def absolutise_urls(html: str, url: str) -> str:
    url_attributes = {
        "a": ["href"],
        "link": ["href"],
        "img": ["src", "srcset"],
        "script": ["src"],
        "iframe": ["src"],
        "source": ["src", "srcset"],
        "video": ["src", "poster"],
        "audio": ["src"],
        "form": ["action"],
    }
    soup = BeautifulSoup(html, "html.parser")
    base_url = "https://" + tldextract.extract(url).top_domain_under_public_suffix

    for tag_name, attributes in url_attributes.items():
        for tag in soup.find_all(tag_name):
            for attr in attributes:
                value = tag.get(attr)

                if not isinstance(value, str):
                    continue

                if attr == "srcset":
                    tag[attr] = ", ".join(
                        (
                            f"{urljoin(base_url, parts[0])}"
                            + (f" {parts[1]}" if len(parts) > 1 else "")
                        )
                        for parts in (part.strip().split() for part in value.split(","))
                    )
                else:
                    tag[attr] = urljoin(base_url, value)

    return str(soup)


def pdf_to_markdown(pdf_content: bytes) -> str:
    doc = pymupdf.open(stream=pdf_content, filetype="pdf")
    md = pymupdf4llm.to_markdown(doc, table_output="html")
    assert isinstance(md, str)
    return md


def html_to_markdown(html: str, url: str) -> str:
    html_with_abs_urls = absolutise_urls(html, url)
    md = markdownify(html_with_abs_urls)
    return md


def image_to_text(image_content: bytes) -> str:
    try:
        image = Image.open(BytesIO(image_content))
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        return "Could not perform OCR on the image, because the tesseract library is not installed."


def word_doc_to_text(doc_content: bytes) -> str:
    doc = WordDocument(BytesIO(doc_content))

    return "\n\n".join(
        paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()
    )


def pp_presentation_to_md(ppp_content: bytes) -> str:
    presentation = PowerPointPresentation(BytesIO(ppp_content))

    slides = []
    for slide_number, slide in enumerate(presentation.slides, 1):
        text = "\n".join(
            shape.text
            for shape in slide.shapes
            if isinstance(shape, pptx.shapes.autoshape.Shape) and shape.text.strip()
        )
        if text.strip():
            slides.append(f"## Slide {slide_number}\n\n{text}")

    return "\n\n".join(slides)


def get_website_contents(url: str) -> str:
    """
    Get the raw html of the website specified by the url.

    Args:
        url: URL of the website to get

    Returns:
        Markdown adapted from the raw contents of the website obtained via a GET request, no javascript or other DOM operations are executed by the website
    """
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        response = requests.get(url)
        response.raise_for_status()

        content_type = (
            response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        )
        match content_type:
            case "application/pdf":
                return pdf_to_markdown(response.content)
            case "text/html":
                return html_to_markdown(response.text, url)
            case s if s.startswith("image"):
                return image_to_text(response.content)
            case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return word_doc_to_text(response.content)
            case "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                return pp_presentation_to_md(response.content)
            case _:
                return response.text

    except Exception:  # noqa: BLE001
        return ""


def perform_exact_search(title: str, limit: int = 10) -> str:
    try:
        matching_contents = ""
        searcher = ddgs.DDGS()
        results = searcher.text(
            query=title,
            max_results=limit,
            safesearch="off",
            region="wt-wt",
        )
        for result in results:
            if (
                title.lower() in result["title"].lower()
                or title.lower() in result["body"]
            ):
                matching_contents += get_website_contents(result["href"])
        return matching_contents
    except ddgs.exceptions.DDGSException:
        return ""


class FailedSource(Enum):
    Failed = auto()


def crawl_sources(sources: dict[str, Source]) -> dict[str, str | FailedSource]:
    all_source_content = {}
    for source_name, source in sources.items():
        source_content = ""
        if source.urls:
            for url in source.urls:
                source_content += get_website_contents(url)
        else:
            source_content = perform_exact_search(source.title)

        if len(source_content) == 0:
            all_source_content[source_name] = FailedSource.Failed
        else:
            all_source_content[source_name] = source_content
    return all_source_content


class Score(NamedTuple):
    value: float
    total: int


def direct_score(fact_content: str, source_content: str) -> float:
    if fact_content in source_content:
        return 1.0
    return fuzz.partial_ratio(fact_content, source_content) / 100


def fact_gathering_score(
    model_output: ProcessedOutput, sources: dict[str, str | FailedSource]
) -> Score:
    score_value = 0.0
    total_facts = 0

    for source_name, fact_list in model_output.stated_facts.items():
        total_facts += len(fact_list)
        source = sources[source_name]
        if source is FailedSource.Failed:
            continue

        source = source.lower()
        for fact in fact_list:
            fact_content = fact.content.lower()
            score_value += direct_score(fact_content, source)

    return Score(value=score_value, total=total_facts)


def search_score(topic: str, key: str, fact_content: str) -> float:
    try:
        searcher = ddgs.DDGS()
        results = searcher.text(
            query=f"{topic} {key} {fact_content}",
            max_results=10,
            safesearch="off",
            region="wt-wt",
        )
        search_scores = []
        for result in results:
            search_contents = get_website_contents(result["href"])
            search_scores.append(direct_score(fact_content, search_contents))
        search_scores.sort()
        return np.mean(search_scores[:-3])
    except ddgs.exceptions.DDGSException:
        return 0.0


def inference_score(
    topic: str, model_output: ProcessedOutput, sources: dict[str, str | FailedSource]
) -> Score:
    score_value = 0.0
    total_facts = 0

    for source_name, fact_list in model_output.inferred_facts.items():
        total_facts += len(fact_list)
        source = sources[source_name]
        if source is FailedSource.Failed:
            continue

        source = source.lower()
        for fact in fact_list:
            fact_content = fact.content.lower()
            direct_score_value = direct_score(fact_content, source)
            search_score_value = search_score(topic, fact.key.lower(), fact_content)
            score_value += max(direct_score_value, search_score_value)

    return Score(value=score_value, total=total_facts)


def hallucinated_score(sources: dict[str, str | FailedSource]) -> Score:
    """Find the number of sources that are hallucinated"""
    score_value = float(len(sources))
    total_sources = len(sources)
    for source_content in sources.values():
        if source_content is FailedSource.Failed:
            score_value -= 1
    return Score(value=score_value, total=total_sources)


def score_output(topic: str, model_output_file: str) -> dict[str, Score]:
    model_output = process_output(model_output_file)
    sources = crawl_sources(model_output.sources)
    return {
        "fact_gathering": fact_gathering_score(model_output, sources),
        "inference": inference_score(topic, model_output, sources),
        "hallucinated": hallucinated_score(sources),
    }


def score_all_outputs(topic: str, output_folder: str) -> dict[str, dict[str, Score]]:
    scores = {}
    for output_file in glob.glob(f"{output_folder}/*.yaml"):
        scores[output_file[output_file.rfind("/") + 1 : output_file.rfind(".")]] = (
            score_output(topic, output_file)
        )
    return scores
