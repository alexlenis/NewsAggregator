from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List, Dict, Any


class MongoDB:
    def __init__(self, uri="mongodb://localhost:27017/", db_name="news_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.articles = self.db.articles

        # unique url ώστε να μην ξαναμπαίνουν άρθρα
        self.articles.create_index("url", unique=True)
        self.articles.create_index("published_at")
        self.articles.create_index("category")
        self.articles.create_index("source")
        self.articles.create_index("tags")

    def insert_article(self, article: Dict[str, Any]) -> bool:
        """
        Δέχεται dict άρθρου (όπως φτιάχνεις στο app και στους scrapers).
        """
        doc = {
            "url": article.get("url"),
            "title": article.get("title"),
            "published_at": article.get("published_at"),
            "category": article.get("category"),
            "source": article.get("source"),
            "image_url": article.get("image_url"),
            "summary": article.get("summary"),
            "tags": article.get("tags") or [],
            "html_content": article.get("html_content"),
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.articles.insert_one(doc)
            return True
        except Exception:
            # πιθανό DuplicateKeyError
            return False

    def get_by_url(self, url: str):
        return self.articles.find_one({"url": url})

    def list_articles(self, limit=20, query=None):
        query = query or {}
        return list(self.articles.find(query).sort("published_at", -1).limit(limit))

    def distinct_sources(self):
        vals = self.articles.distinct("source")
        return sorted([v for v in vals if v])

    def distinct_categories(self):
        vals = self.articles.distinct("category")
        return sorted([v for v in vals if v])
