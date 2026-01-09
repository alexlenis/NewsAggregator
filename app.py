from flask import Flask, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from mongo import MongoDB

app = Flask(__name__)
app.secret_key = "supersecret-change-me"  # βάλε κάτι δικό σου
db = MongoDB()

# ------------------ HELPERS ------------------
def require_admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return None


# ------------------ PUBLIC ------------------
@app.route("/")
def home():
    # φίλτρα
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
        # αναζήτηση σε τίτλο/summary
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
    # απλό login (όπως συνήθως ζητάνε σε εργασίες)
    # *Αν θες πιο “σωστό”, το κάνουμε με hashed password & users collection.*
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == "admin" and p == "1234":
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
            "url": request.form.get("url"),
            "title": request.form.get("title"),
            "published_at": request.form.get("published_at"),
            "category": request.form.get("category"),
            "source": request.form.get("source"),  # νέο πεδίο
            "image_url": request.form.get("image_url"),
            "summary": request.form.get("summary"),
            "tags": [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()],
            "html_content": request.form.get("html_content"),
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
            "url": request.form.get("url"),
            "title": request.form.get("title"),
            "published_at": request.form.get("published_at"),
            "category": request.form.get("category"),
            "source": request.form.get("source"),
            "image_url": request.form.get("image_url"),
            "summary": request.form.get("summary"),
            "tags": [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()],
            "html_content": request.form.get("html_content"),
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

    import subprocess, sys

    source = request.form.get("source", "all")
    pages = request.form.get("pages", "1").strip()
    delay = request.form.get("delay", "1.0").strip()

    try:
        pages_i = max(1, int(pages))
    except ValueError:
        pages_i = 1

    try:
        delay_f = float(delay)
        if delay_f < 0:
            delay_f = 1.0
    except ValueError:
        delay_f = 1.0

    # τρέχουμε τα δικά σου αρχεία (σωστά ονόματα)
    if source == "naftemporiki":
        subprocess.run([sys.executable, "scraper_na.py", "--pages", str(pages_i), "--delay", str(delay_f)], check=False)
        flash("Έγινε scraping από Ναυτεμπορική")
    elif source == "kathimerini":
        subprocess.run([sys.executable, "scraper_ka.py", "--pages", str(pages_i), "--delay", str(delay_f)], check=False)
        flash("Έγινε scraping από Καθημερινή")
    else:
        subprocess.run([sys.executable, "scraperall.py", "--pages", str(pages_i), "--delay", str(delay_f)], check=False)
        flash("Έγινε scraping από όλες τις πηγές")

    return redirect(url_for("admin"))


# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(debug=True)
