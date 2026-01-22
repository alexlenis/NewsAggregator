import argparse
import time
import logging
from urllib.parse import urljoin, urldefrag
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from mongo import MongoDB

BASE = "https://www.naftemporiki.gr"
LISTING = BASE + "/newsroom/"

HEADERS = {"User-Agent": "NewsAggregatorBot/1.0 (+project)"}
logger = logging.getLogger("naftemporiki")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_soup(url, session):
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_links(soup):
    """
    Η newsroom της Ναυτεμπορικής δεν εγγυάται <article> tags.
    Παίρνουμε όλα τα anchors και κρατάμε όσα μοιάζουν με άρθρα (heuristic).
    """
    links = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue

        full = urljoin(BASE, href)
        full, _ = urldefrag(full)

        # heuristic: άρθρα συνήθως έχουν αρκετά segments και δεν είναι newsroom/page
        if "naftemporiki.gr" not in full:
            continue
        if "/newsroom" in full:
            continue

        # κράτα URLs που μοιάζουν με άρθρα (συνήθως έχουν αριθμητικό id ή αρκετό path)
        # (ασφαλές heuristic χωρίς να “κλειδώνει” σε ένα μόνο pattern)
        path = full.replace(BASE, "")
        if any(ch.isdigit() for ch in path) and len(path.split("/")) >= 3:
            links.add(full)

    return list(links)


def extract_body_html(soup: BeautifulSoup) -> str | None:
    """
    Robust body extractor για Ναυτεμπορική: πολλά fallbacks.
    Στόχος: να μη μένει το html_content None.
    """
    selectors = [
        "div.article__main",
        "div.article__content",
        "div.entry-content",
        "div[itemprop='articleBody']",
        "article .article__body",
        "article",
        "main",
    ]

    node = None
    for sel in selectors:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            break

    if not node:
        return None

    # καθαρίζουμε “άχρηστα” blocks που συχνά υπάρχουν μέσα στο main/article
    for bad in node.select("nav, aside, footer, form, script, style"):
        bad.decompose()

    html = str(node).strip()
    # αν το κείμενο είναι υπερβολικά μικρό, το θεωρούμε ότι δεν βρήκαμε σώμα
    text_len = len(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if text_len < 150:
        return None

    return html


def extract_tags(soup: BeautifulSoup) -> list[str]:
    """
    Tags: πρώτα δοκιμάζουμε ul.tags, μετά fallbacks.
    """
    tags = []

    tag_block = soup.find("ul", class_="tags")
    if tag_block:
        for a in tag_block.find_all("a"):
            t = a.get_text(strip=True)
            if t:
                tags.append(t)

    if not tags:
        for a in soup.select("a[rel='tag'], a[href*='/tag/']"):
            t = a.get_text(strip=True)
            if t and t not in tags:
                tags.append(t)

    return tags


def parse_article(url, session):
    soup = get_soup(url, session)
    if not soup:
        return None

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

    tags = extract_tags(soup)
    html_content = extract_body_html(soup)

    # log για να ξέρεις αν συνεχίζει να χάνει body
    if html_content is None:
        logger.info(f"Body not found (html_content=None) for: {url}")

    return {
        "source": "naftemporiki",
        "url": url,
        "title": title,
        "published_at": published_at,
        "category": category,
        "image_url": image_url,
        "summary": summary,
        "tags": tags,
        "html_content": html_content,
    }


def crawl(pages=1, delay=1.0):
    session = requests.Session()
    db = MongoDB()
    added = 0

    for page in range(1, pages + 1):
        # Σημείωση: Αν η newsroom δεν δουλεύει με ?page=, άλλαξέ το σε /page/{page}/
        url = LISTING + (f"?page={page}" if page > 1 else "")
        soup = get_soup(url, session)
        if not soup:
            continue

        links = extract_links(soup)
        logger.info(f"Listing page {page}: {len(links)} links found")

        for link in links:
            if db.get_by_url(link):
                continue

            article = parse_article(link, session)
            if article and article.get("url") and article.get("title"):
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
