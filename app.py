from flask import Flask, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from mongo import MongoDB

app = Flask(__name__)
app.secret_key = "supersecret"  # άλλαξέ το σε κάτι δικό σου
db = MongoDB()

# ------------------ PUBLIC ------------------
@app.route("/")
def home():
    category = request.args.get("category")
    if category:
        # Φίλτρο κατηγορίας (case-insensitive)
        articles = db.articles.find(
            {"category": {"$regex": category, "$options": "i"}}
        ).sort("published_at", -1).limit(20)
        articles = list(articles)
    else:
        articles = db.list_articles(limit=20)

    return render_template("public.html", articles=articles)

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            flash("Επιτυχής σύνδεση")
            return redirect(url_for("admin"))
        else:
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
    if not session.get("admin"):
        return redirect(url_for("login"))
    articles = db.list_articles(limit=100)
    return render_template("admin.html", articles=articles)

# ------------------ CREATE ------------------
@app.route("/create", methods=["GET", "POST"])
def create_article():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        article = {
            "url": request.form["url"],
            "title": request.form["title"],
            "published_at": request.form["published_at"],
            "category": request.form["category"],
            "image_url": request.form["image_url"],
            "summary": request.form["summary"],
            "tags": [t.strip() for t in request.form["tags"].split(",") if t.strip()],
            "html_content": request.form["html_content"],
        }
        db.insert_article(article)
        flash("Το άρθρο δημιουργήθηκε")
        return redirect(url_for("admin"))
    return render_template("create.html")

# ------------------ UPDATE ------------------
@app.route("/update/<id>", methods=["GET", "POST"])
def update_article(id):
    if not session.get("admin"):
        return redirect(url_for("login"))
    article = db.articles.find_one({"_id": ObjectId(id)})
    if not article:
        flash("Δεν βρέθηκε το άρθρο")
        return redirect(url_for("admin"))

    if request.method == "POST":
        update_data = {
            "url": request.form["url"],
            "title": request.form["title"],
            "published_at": request.form["published_at"],
            "category": request.form["category"],
            "image_url": request.form["image_url"],
            "summary": request.form["summary"],
            "tags": [t.strip() for t in request.form["tags"].split(",") if t.strip()],
            "html_content": request.form["html_content"],
        }
        db.articles.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash("Το άρθρο ενημερώθηκε")
        return redirect(url_for("admin"))

    return render_template("update.html", article=article)

# ------------------ DELETE ------------------
@app.route("/delete/<id>")
def delete_article(id):
    if not session.get("admin"):
        return redirect(url_for("login"))
    db.articles.delete_one({"_id": ObjectId(id)})
    flash("Το άρθρο διαγράφηκε")
    return redirect(url_for("admin"))

# ------------------ SCRAPERS ------------------
@app.route("/scrape/<source>")
def run_scraper(source):
    import subprocess, sys

    if source == "naftemporiki":
        subprocess.run([sys.executable, "scraper_naftemporiki_mongo.py", "--pages", "1"])
        flash("Έγινε scraping από Ναυτεμπορική")
    elif source == "kathimerini":
        subprocess.run([sys.executable, "scraper_kathimerini_mongo.py", "--pages", "1"])
        flash("Έγινε scraping από Καθημερινή")
    elif source == "all":
        subprocess.run([sys.executable, "scrape_all.py"])
        flash("Έγινε scraping από όλες τις πηγές")
    return redirect(url_for("admin"))

# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(debug=True)
