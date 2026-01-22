import argparse
import time
import logging
from urllib.parse import urljoin, urldefrag
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from mongo import MongoDB

BASE = "https://www.kathimerini.gr"
LISTING = BASE + "/epikairothta/"

HEADERS = {"User-Agent": "NewsAggregatorBot/1.0 (+project)"}
logger = logging.getLogger("kathimerini")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_session() -> requests.Session:
    """
    Session με retries για transient errors (429/5xx).
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_soup(url: str, session: requests.Session):
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_links(soup: BeautifulSoup):
    """
    Παίρνει links από listings. Κρατάμε set για uniqueness.
    """
    links = set()
    for art in soup.find_all("article"):
        a = art.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        full = urljoin(BASE, href)
        full, _ = urldefrag(full)  # ✅ remove #fragment
        links.add(full)
    return list(links)


def canonicalize_url(soup: BeautifulSoup, fallback_url: str) -> str:
    """
    Αν υπάρχει canonical, το χρησιμοποιούμε για dedup.
    """
    canon = soup.find("link", rel="canonical", href=True)
    if canon and canon.get("href"):
        u = urljoin(BASE, canon["href"])
        u, _ = urldefrag(u)
        return u
    return fallback_url


def parse_article(url: str, session: requests.Session):
    soup = get_soup(url, session)
    if not soup:
        return None

    # canonical url (βοηθά dedup)
    url = canonicalize_url(soup, url)

    title = soup.find("meta", property="og:title")
    title = title["content"].strip() if title and title.get("content") else None
    if not title and soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    pub = soup.find("meta", property="article:published_time")
    pub = pub["content"].strip() if pub and pub.get("content") else None
    published_at = dateparser.parse(pub).isoformat() if pub else None

    cat = soup.find("meta", property="article:section")
    category = cat["content"].strip() if cat and cat.get("content") else None

    img = soup.find("meta", property="og:image")
    image_url = img["content"].strip() if img and img.get("content") else None

    desc = soup.find("meta", attrs={"name": "description"})
    summary = desc["content"].strip() if desc and desc.get("content") else None

    tags = []
    tag_block = soup.find("ul", class_="tags")
    if tag_block:
        for a in tag_block.find_all("a"):
            t = a.get_text(strip=True)
            if t:
                tags.append(t)
    else:
        logger.info(f"No tags found for: {url}")

    body = soup.find("div", class_="entry-content")
    html_content = str(body) if body else None
    if not html_content:
        logger.info(f"No body content found for: {url}")

    return {
        "source": "kathimerini",
        "url": url,
        "title": title,
        "published_at": published_at,
        "category": category,
        "image_url": image_url,
        "summary": summary,
        "tags": tags,
        "html_content": html_content,
    }


def crawl(pages: int = 1, delay: float = 1.0):
    session = make_session()
    db = MongoDB()
    added = 0

    for page in range(1, pages + 1):
        url = LISTING + f"?page={page}"
        soup = get_soup(url, session)
        if not soup:
            continue

        links = extract_links(soup)
        logger.info(f"Listing page {page}: {len(links)} links found")

        for link in links:
            # ✅ link already defragged in extract_links, but safe to do again:
            link, _ = urldefrag(link)

            if db.get_by_url(link):
                continue

            article = parse_article(link, session)
            if not article:
                continue

            # Αν canonical URL διαφορετικό, ξανα-τσέκαρε dedup
            if article.get("url") and db.get_by_url(article["url"]):
                continue

            if article.get("url") and article.get("title"):
                if db.insert_article(article):
                    added += 1
                    logger.info(f"Inserted: {article['title']}")
            time.sleep(delay)

    logger.info(f"Done. Added {added} new articles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    crawl(pages=args.pages, delay=args.delay)
