import argparse
import logging
import time

# Εισαγωγή των δύο scrapers
import scraper_na as na
import scraper_ka as ka

logger = logging.getLogger("scrape_all")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def scrape_all(pages=2, delay=1.0, sources=None):
    """
    Τρέχει scrapers για Ναυτεμπορική και Καθημερινή.
    sources: λίστα π.χ. ["naftemporiki", "kathimerini"]
    """
    if not sources or "naftemporiki" in sources:
        logger.info("Ξεκινάει scraping Ναυτεμπορικής...")
        na.crawl(pages=pages, delay=delay)
        time.sleep(3)

    if not sources or "kathimerini" in sources:
        logger.info("Ξεκινάει scraping Καθημερινής...")
        ka.crawl(pages=pages, delay=delay)
        time.sleep(3)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1, help="Πόσες σελίδες να κατεβάσει από κάθε site")
    parser.add_argument("--delay", type=float, default=1.0, help="Καθυστέρηση μεταξύ αιτημάτων (σε δευτ.)")
    parser.add_argument("--sources", nargs="+", choices=["naftemporiki", "kathimerini"], help="Ποιες πηγές να τρέξουν")
    args = parser.parse_args()

    scrape_all(pages=args.pages, delay=args.delay, sources=args.sources)
