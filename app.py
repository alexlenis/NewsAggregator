import os
import sys
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from mongo import MongoDB

app = Flask(__name__)

# ---- Portfolio-friendly config via ENV ----
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "news_db")

db = MongoDB(uri=MONGO_URI, db_name=MONGO_DB)


# ------------------ HELPERS ------------------
def require_admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return None


def parse_tags_csv(s: str):
    return [t.strip() for t in (s or "").split(",") if t.strip()]


# ------------------ PUBLIC ------------------
@app.route("/")
def home():
    category = (request.args.get("category") or "").strip()
    source = (request.args.get("source") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    q = (request.args.get("q") or "").strip()

    query = {}

    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if source:
        query["source"] = {"$regex": f"^{source}$", "$options": "i"}
    if tag:
        query["tags"] = {"$elemMatch": {"$regex": tag, "$options": "i"}}
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"summary": {"$regex": q, "$options": "i"}},
        ]

    articles = db.list_articles(limit=30, query=query)
    sources = db.distinct_sources()
    categories = db.distinct_categories()

    return render_template(
        "public.html",
        articles=articles,
        sources=sources,
        categories=categories,
    )


@app.route("/article/<id>")
def view_article(id):
    a = db.articles.find_one({"_id": ObjectId(id)})
    if not a:
        flash("Δεν βρέθηκε άρθρο.")
        return redirect(url_for("home"))
    return render_template("article.html", a=a)


# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            flash("Επιτυχής σύνδεση")
            return redirect(url_for("admin"))
        flash("Λάθος στοιχεία")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Αποσυνδέθηκες")
    return redirect(url_for("home"))


# ------------------ ADMIN ------------------
@app.route("/admin")
def admin():
    guard = require_admin()
    if guard:
        return guard

    articles = db.list_articles(limit=200)
    return render_template("admin.html", articles=articles)


# ------------------ CREATE ------------------
@app.route("/create", methods=["GET", "POST"])
def create_article():
    guard = require_admin()
    if guard:
        return guard

    if request.method == "POST":
        article = {
            "url": (request.form.get("url") or "").strip(),
            "title": (request.form.get("title") or "").strip(),
            "published_at": (request.form.get("published_at") or "").strip() or None,
            "category": (request.form.get("category") or "").strip() or None,
            "source": (request.form.get("source") or "").strip() or None,
            "image_url": (request.form.get("image_url") or "").strip() or None,
            "summary": (request.form.get("summary") or "").strip() or None,
            "tags": parse_tags_csv(request.form.get("tags")),
            "html_content": request.form.get("html_content") or None,
        }
        ok = db.insert_article(article)
        flash("Το άρθρο δημιουργήθηκε" if ok else "Δεν προστέθηκε (πιθανό duplicate URL).")
        return redirect(url_for("admin"))

    return render_template("create.html")


# ------------------ UPDATE ------------------
@app.route("/update/<id>", methods=["GET", "POST"])
def update_article(id):
    guard = require_admin()
    if guard:
        return guard

    article = db.articles.find_one({"_id": ObjectId(id)})
    if not article:
        flash("Δεν βρέθηκε το άρθρο")
        return redirect(url_for("admin"))

    if request.method == "POST":
        update_data = {
            "url": (request.form.get("url") or "").strip(),
            "title": (request.form.get("title") or "").strip(),
            "published_at": (request.form.get("published_at") or "").strip() or None,
            "category": (request.form.get("category") or "").strip() or None,
            "source": (request.form.get("source") or "").strip() or None,
            "image_url": (request.form.get("image_url") or "").strip() or None,
            "summary": (request.form.get("summary") or "").strip() or None,
            "tags": parse_tags_csv(request.form.get("tags")),
            "html_content": request.form.get("html_content") or None,
        }
        db.articles.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash("Το άρθρο ενημερώθηκε")
        return redirect(url_for("admin"))

    return render_template("update.html", article=article)


# ------------------ DELETE ------------------
@app.route("/delete/<id>")
def delete_article(id):
    guard = require_admin()
    if guard:
        return guard

    db.articles.delete_one({"_id": ObjectId(id)})
    flash("Το άρθρο διαγράφηκε")
    return redirect(url_for("admin"))


# ------------------ SCRAPERS (RUN FROM BACKEND) ------------------
@app.route("/scrape", methods=["POST"])
def run_scraper():
    guard = require_admin()
    if guard:
        return guard

    source = request.form.get("source", "all")

    # pages: clamp 1..50 (ταιριάζει και με το input max=50)
    pages_raw = (request.form.get("pages", "1") or "1").strip()
    try:
        pages_i = int(pages_raw)
    except ValueError:
        pages_i = 1
    pages_i = max(1, min(50, pages_i))

    # delay
    delay_raw = (request.form.get("delay", "1.0") or "1.0").strip()
    try:
        delay_f = float(delay_raw)
    except ValueError:
        delay_f = 1.0
    if delay_f < 0:
        delay_f = 1.0

    if source == "naftemporiki":
        cmd = [sys.executable, "scraper_na.py", "--pages", str(pages_i), "--delay", str(delay_f)]
        msg = "Έγινε scraping από Ναυτεμπορική"
    elif source == "kathimerini":
        cmd = [sys.executable, "scraper_ka.py", "--pages", str(pages_i), "--delay", str(delay_f)]
        msg = "Έγινε scraping από Καθημερινή"
    else:
        cmd = [sys.executable, "scraperall.py", "--pages", str(pages_i), "--delay", str(delay_f)]
        msg = "Έγινε scraping από όλες τις πηγές"

    # timeout ώστε να μην “κολλάει” για πάντα (portfolio-friendly)
    subprocess.run(cmd, check=False, timeout=600)

    flash(msg)
    return redirect(url_for("admin"))


# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,debug=True)
