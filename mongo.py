# db_mongo.py
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List

class MongoDB:
    def __init__(self, uri="mongodb://localhost:27017/", db_name="news_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.articles = self.db.articles
        # unique index στο url για να μην ξαναμπαίνουν άρθρα
        self.articles.create_index("url", unique=True)

    def insert_article(self,
                       url: str,
                       title: str,
                       published_at: Optional[str],
                       category: Optional[str],
                       image_url: Optional[str],
                       summary: Optional[str],
                       tags: Optional[List[str]],
                       html_content: Optional[str]) -> bool:
        doc = {
            "url": url,
            "title": title,
            "published_at": published_at,
            "category": category,
            "image_url": image_url,
            "summary": summary,
            "tags": tags or [],
            "html_content": html_content,
            "created_at": datetime.now().isoformat()
        }
        try:
            self.articles.insert_one(doc)
            return True
        except Exception:
            # πιθανόν DuplicateKeyError
            return False

    def get_by_url(self, url: str):
        return self.articles.find_one({"url": url})

    def list_articles(self, limit=10):
        return list(self.articles.find().sort("published_at", -1).limit(limit))
