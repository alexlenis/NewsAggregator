import os
import time
import logging
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError, OperationFailure

logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self, uri=None, db_name=None):
        # παίρνει από env (Docker) αλλιώς fallback για local
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = db_name or os.getenv("MONGO_DB", "news_db")

        # μικρό timeout για να μη “κρεμάει” request
        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[self.db_name]
        self.articles = self.db.articles

        # περίμενε λίγο να σηκωθεί η Mongo (πολύ χρήσιμο στο docker-compose)
        self._wait_for_mongo()

        # indexes (ασφαλώς)
        self._ensure_indexes()

    def _wait_for_mongo(self, retries: int = 10, delay: float = 0.8):
        for i in range(retries):
            try:
                # ping για να επιβεβαιώσουμε σύνδεση
                self.client.admin.command("ping")
                return
            except ServerSelectionTimeoutError:
                logger.warning("Mongo not ready yet (%s/%s)...", i + 1, retries)
                time.sleep(delay)

        # αν μετά από retries δεν είναι έτοιμη, το αφήνουμε να σκάσει καθαρά
        raise ServerSelectionTimeoutError(f"MongoDB not reachable at {self.uri}")

    def _ensure_indexes(self):
        try:
            self.articles.create_index("url", unique=True)
            self.articles.create_index("published_at")
            self.articles.create_index("category")
            self.articles.create_index("source")
            self.articles.create_index("tags")
        except OperationFailure:
            # δεν πρέπει να ρίχνει όλο το app αν υπάρχει πρόβλημα σε index
            logger.exception("Index creation failed (OperationFailure)")
        except Exception:
            logger.exception("Index creation failed")

    def insert_article(self, article) -> bool:
        doc = {**article, "created_at": datetime.utcnow().isoformat()}
        try:
            self.articles.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False
        except Exception:
            logger.exception("Insert failed")
            return False

    def get_by_url(self, url):
        return self.articles.find_one({"url": url})

    def list_articles(self, limit=20, query=None):
        return list(self.articles.find(query or {}).sort("published_at", -1).limit(limit))

    def distinct_sources(self):
        return sorted([v for v in self.articles.distinct("source") if v])

    def distinct_categories(self):
        return sorted([v for v in self.articles.distinct("category") if v])
