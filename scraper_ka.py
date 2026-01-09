import argparse
import time
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from mongo import MongoDB

BASE = "https://www.kathimerini.gr"
LISTING = BASE + "/epikairothta/"

HEADERS = {"User-Agent": "NewsAggregatorBot/1.0 (+project)"}
logger = logging.getLogger("kathimerini")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_soup(url, session):
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_links(soup):
    links = set()
    for art in soup.find_all("article"):
        a = art.find("a", href=True)
        if a:
            links.add(urljoin(BASE, a["href"]))
    return list(links)


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

    tags = []
    tag_block = soup.find("ul", class_="tags")
    if tag_block:
        for a in tag_block.find_all("a"):
            t = a.get_text(strip=True)
            if t:
                tags.append(t)

    body = soup.find("div", class_="entry-content")
    html_content = str(body) if body else None

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


def crawl(pages=1, delay=1.0):
    session = requests.Session()
    db = MongoDB()
    added = 0

    for page in range(1, pages + 1):
        url = LISTING + f"?page={page}"
        soup = get_soup(url, session)
        if not soup:
            continue

        links = extract_links(soup)
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
