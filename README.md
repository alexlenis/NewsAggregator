# 📰 News Aggregator

A web-based news aggregator application that collects, stores, and displays news
articles from Greek news websites in a mash-up format (similar to Google News).

## 🚀 Features
- Web scraping from Greek news portals:
  - Naftemporiki
  - Kathimerini
- Storage of news articles in MongoDB
- Public-facing news feed
- Filtering by category and source
- Admin panel with authentication
- Full CRUD functionality for articles
- Ability to run web scrapers directly from the backend

## 🛠️ Tech Stack
- Python
- Flask
- MongoDB
- BeautifulSoup & Requests
- Bootstrap

## 📄 Article Data
Each article contains:
- Title
- Publication date and time
- Category
- Source
- Article URL
- Image URL
- Summary
- Tags
- Full HTML content

## ▶️ How to Run
1. Start MongoDB (default: localhost:27017)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt

Run the application:
python app.py

Open your browser at:
http://127.0.0.1:5000

🔐 Admin Access

Username: admin

Password: 1234

📌 Notes

This project was developed as part of an academic assignment and simulates
a real-world news aggregation system.
