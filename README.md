📰 News Aggregator

A full-stack news aggregation platform that collects articles from multiple Greek news sources, stores them in MongoDB, and presents them through a modern web interface with filtering, tagging, and administrative management.

The project is fully **dockerized**, reproducible on any machine, and designed as a **portfolio-ready application**.

---

## ✨ Features

- 🕷️ Web scraping from multiple news sources (e.g. Kathimerini, Naftemporiki)
- 🗄️ MongoDB storage with proper indexing
- 🚫 Duplicate article prevention (unique URL index)
- 🔎 Search and filtering by source, category, and tags
- 🖼️ Article preview with images and metadata
- 🔐 Admin panel for content management
- 🐳 Fully Dockerized (no local setup required)

---

## 🧱 Tech Stack

- **Backend**: Python (Flask)
- **Database**: MongoDB
- **Scraping**: Requests, BeautifulSoup
- **Frontend**: Jinja2, HTML, CSS
- **Containerization**: Docker, Docker Compose

---

## 📁 Project Structure

```text
NewsAggregator/
│
├── app.py                 # Flask application entry point
├── mongo.py               # MongoDB abstraction & indexes
├── scraper_ka.py          # Kathimerini scraper
├── scraper_na.py          # Naftemporiki scraper
├── scraperall.py          # Run all scrapers
│
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, images, assets
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
├── .env.example           # Environment variables template
├── .gitignore
└── README.md
🚀 Quick Start (Docker)
Prerequisites
Docker

Docker Compose

No Python, virtualenv, or MongoDB installation required.

1️⃣ Clone the repository
git clone https://github.com/alexlenis/NewsAggregator.git
cd NewsAggregator
2️⃣ Create environment variables
cp .env.example .env
The .env file is ignored by Git and used only locally or inside Docker.

3️⃣ Build & run the application
docker compose up --build
4️⃣ Open the application
🌐 Web UI: http://localhost:5000

🗄️ MongoDB runs inside Docker (internal network)

🔐 Admin Access (Demo)
For demonstration and evaluation purposes, the application includes a predefined administrator account.

Admin credentials:

Username: admin
Password: 1234
With admin access, a reviewer can:

Access the admin panel

Create, edit, and delete articles

Manually trigger scraping

Manage aggregated content

⚠️ Important Note
These credentials are intentionally simple and hardcoded only for demo / portfolio use.
In a production system, authentication would be implemented using secure password hashing and environment-based secrets.

🕷️ Running the Scrapers
Scraping is executed inside the web container.

To run all scrapers:

docker compose exec web python scraperall.py
Scrapers support:

Page limits

Delay between requests

Source selection

🗄️ Database Design
MongoDB database: news_db
Collection: articles

Indexes:

url (unique)

published_at

category

source

tags

This ensures:

Fast queries

Clean data

No duplicate articles

🔧 Environment Variables
Example (.env.example):

MONGO_URI=mongodb://mongo:27017/
MONGO_DB=news_db
FLASK_ENV=development
Sensitive configuration is never committed to the repository.

🧠 Design Decisions
Docker-first architecture for reproducibility

MongoDB for flexible article schema

One scraper per source for maintainability

Unique URL index to prevent duplicates

Clear separation between scraping, storage, and presentation

📌 Why this project?
This project demonstrates:

Real-world backend development

Web scraping with error handling

Database modeling & indexing

Docker & container orchestration

Clean Git and environment practices

It is designed to be easy to run, review, and extend.

🔮 Possible Improvements
Automated scheduling (cron / Celery)

REST API

User accounts & personalization

Full-text search

Cloud deployment

👤 Author
Alex Lenis
GitHub: https://github.com/alexlenis

📄 License
This project is intended for educational and portfolio purposes.
