import json
import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HACKERRANK_SUPPORT_URL = "https://support.hackerrank.com/"
CLAUDE_SUPPORT_URL = "https://support.claude.com/en/"
VISA_SUPPORT_URL = "https://www.visa.co.in/support.html"


def save_chunks(chunks: list, domain: str) -> None:
    """Save scraped chunks to corpus/{domain}/chunks.json."""
    output_path = f"corpus/{domain}/chunks.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"    → Saved {len(chunks)} chunks to {output_path}")


def scrape_hackerrank() -> list:
    """Crawl HackerRank support content and return article chunks."""
    chunks = []

    # Step 1 — get all collection URLs from homepage
    response = requests.get(HACKERRANK_SUPPORT_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    collection_urls = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/collections/"):
            full_url = urljoin(HACKERRANK_SUPPORT_URL, href)
            collection_urls.add(full_url)

    print(f"    → Found {len(collection_urls)} collections")

    # Step 2 — for each collection, get all article URLs
    article_urls = set()
    for collection_url in collection_urls:
        try:
            response = requests.get(collection_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", class_="kb-article-card", href=True):
                href = a_tag["href"]
                if href.startswith("/articles/"):
                    full_url = urljoin(HACKERRANK_SUPPORT_URL, href)
                    article_urls.add(full_url)
        except requests.RequestException as e:
            print(f"    → Failed to scrape collection {collection_url}: {e}")
            continue

    print(f"    → Found {len(article_urls)} articles")

    # Step 3 — for each article URL, extract kb-article-body text
    for article_url in article_urls:
        try:
            response = requests.get(article_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            article_body = soup.find("div", class_="kb-article-body")

            if not article_body:
                continue

            article_text = article_body.get_text(separator=" ", strip=True)

            if not article_text:
                continue

            chunks.append({
                "text": article_text,
                "source": article_url,
                "domain": "hackerrank",
            })

        except requests.RequestException as e:
            print(f"    → Failed to scrape article {article_url}: {e}")
            continue

    return chunks


def scrape_claude() -> list:
    """Crawl Claude support content and return article chunks."""
    chunks = []

    # Step 1 — get all collection URLs from homepage
    response = requests.get(CLAUDE_SUPPORT_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    collection_urls = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/en/collections/" in href:
            full_url = href if href.startswith("http") else urljoin(CLAUDE_SUPPORT_URL, href)
            collection_urls.add(full_url)

    print(f"    → Found {len(collection_urls)} Claude collections")

    # Step 2 — for each collection URL, find all article links
    article_urls = set()
    for collection_url in collection_urls:
        try:
            response = requests.get(collection_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/en/articles/" in href:
                    full_url = href if href.startswith("http") else urljoin(CLAUDE_SUPPORT_URL, href)
                    article_urls.add(full_url)
        except requests.RequestException as e:
            print(f"    → Failed to scrape collection {collection_url}: {e}")
            continue

    print(f"    → Found {len(article_urls)} Claude articles")

    # Step 3 — for each article URL, extract article_body text
    for article_url in article_urls:
        try:
            response = requests.get(article_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            article_body = soup.find("div", class_="article_body")

            if not article_body:
                continue

            article_text = article_body.get_text(separator=" ", strip=True)

            if not article_text:
                continue

            chunks.append({
                "text": article_text,
                "source": article_url,
                "domain": "claude",
            })

        except requests.RequestException as e:
            print(f"    → Failed to scrape article {article_url}: {e}")
            continue

    return chunks


def scrape_visa() -> list:
    """Scrape Visa support FAQ page and return Q&A chunks."""
    chunks = []

    try:
        response = requests.get(VISA_SUPPORT_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for dt_tag in soup.find_all("dt"):
            question_button = dt_tag.find("button", class_="vs-accordion-button")

            if not question_button:
                continue

            question = question_button.get_text(separator=" ", strip=True)

            if not question:
                continue

            answer_dd = dt_tag.find_next_sibling("dd", class_="vs-accordion-item")

            if not answer_dd:
                continue

            answer = answer_dd.get_text(separator=" ", strip=True)

            if not answer:
                continue

            chunks.append({
                "text": f"Q: {question}\nA: {answer}",
                "source": VISA_SUPPORT_URL,
                "domain": "visa",
            })

    except requests.RequestException as e:
        print(f"    → Failed to scrape Visa support page: {e}")

    return chunks


def build_corpus() -> None:
    """Scrape all three support sites and save to corpus folders."""
    print("[*] Scraping HackerRank support...")
    hr_chunks = scrape_hackerrank()
    save_chunks(hr_chunks, "hackerrank")
    print(f"    → HackerRank: {len(hr_chunks)} chunks saved")

    print("[*] Scraping Claude support...")
    claude_chunks = scrape_claude()
    save_chunks(claude_chunks, "claude")
    print(f"    → Claude: {len(claude_chunks)} chunks saved")

    print("[*] Scraping Visa support...")
    visa_chunks = scrape_visa()
    save_chunks(visa_chunks, "visa")
    print(f"    → Visa: {len(visa_chunks)} chunks saved")

    total = len(hr_chunks) + len(claude_chunks) + len(visa_chunks)
    print(f"\n[✓] Corpus build complete. Total chunks: {total}")


if __name__ == "__main__":
    build_corpus()