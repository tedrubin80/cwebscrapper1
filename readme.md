# Criterion Collection Tracker

A web application that automatically scrapes and tracks releases from The Criterion Collection, featuring a beautiful interface and automated updates.

![Screenshot](https://via.placeholder.com/800x400/667eea/ffffff?text=Criterion+Collection+Tracker)

## ✨ Features

- 🎬 **Automated Scraping** - Fetches latest releases and upcoming films every 24 hours
- 🌐 **Beautiful Web Interface** - Responsive design that works on all devices  
- 🔍 **Search & Filter** - Find films by title, director, spine number, or release status
- 📱 **RESTful API** - JSON endpoints for integration with other applications
- 📊 **Real-time Status** - Monitor scraping progress and system health
- 📥 **Data Export** - Download complete dataset as JSON
- ☁️ **Cloud Ready** - Optimized for DigitalOcean App Platform deployment

## 🚀 Quick Deploy to DigitalOcean

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/tedrubin80/criterion-tracker/tree/main)

### 1. Fork This Repository

1. Click the "Fork" button at the top right of this repository
2. Clone your fork locally:
```bash
git clone https://github.com/tedrubin80/criterion-tracker.git
cd criterion-tracker
```

### 2. Update Configuration

Edit `.app.yaml` and replace `tedrubin80` with your GitHub username:
```yaml
github:
  repo: tedrubin80/criterion-tracker
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Deploy to DigitalOcean App Platform

1. **Login to DigitalOcean** → [cloud.digitalocean.com](https://cloud.digitalocean.com)
2. **Navigate to Apps** → Create App
3. **Choose GitHub** as source
4. **Select your repository** → `criterion-tracker`
5. **Choose branch** → `main`
6. **Review Configuration** (should auto-detect from `.app.yaml`)
7. **Add Environment Variables:**
   - `SECRET_KEY`: Your generated secret key
   - `FLASK_ENV`: `production`
8. **Deploy** → Takes ~5 minutes

Your app will be available at: `https://criterion-tracker-xxxxx.ondigitalocean.app`

## 📁 Project Structure

```
criterion-tracker/
├── app.py                      # Main Flask application
├── criterion_scraper.py        # Web scraping module
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version
├── .app.yaml                   # DigitalOcean configuration
├── Procfile                    # Heroku configuration (optional)
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Dashboard
│   ├── all_releases.html      # Browse films
│   ├── film_detail.html       # Individual film page
│   └── status.html            # System status
└── README.md                  # This file
```

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- Git

### Setup
```bash
# Clone the repository
git clone https://github.com/tedrubin80/criterion-tracker.git
cd criterion-tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key
export DATABASE_PATH=criterion_releases.db

# Run the application
python app.py
```

Visit: `http://localhost:8080`

### Development Commands
```bash
# Run with debug mode
FLASK_ENV=development python app.py

# Test the scraper manually
python -c "from criterion_scraper import CriterionScraper; CriterionScraper().run_scraper()"

# Export current data
curl http://localhost:8080/export > backup.json
```

## 🔄 Automation Features

### Automatic Scraping
- **Frequency**: Every 24 hours
- **Method**: Background thread in the Flask app
- **Failsafe**: Continues even if individual scrapes fail
- **Logging**: Comprehensive logs for debugging

### Manual Triggers
- **Web Interface**: Click "Update Now" button
- **API Endpoint**: `POST /api/scrape`
- **Status Monitoring**: Real-time progress tracking

### External Automation (Optional)
Set up external cron job to trigger scraping:

```bash
# Using cron-job.org or similar service
# POST to: https://your-app.ondigitalocean.app/api/scrape
# Schedule: 0 9 * * * (daily at 9 AM)
```

## 🌐 API Documentation

### Endpoints

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/api/films` | GET | Get films with filters | `?status=released&limit=10` |
| `/api/stats` | GET | Database statistics | Returns counts and status |
| `/api/scrape` | POST | Trigger manual scrape | Starts background scraping |
| `/export` | GET | Download complete dataset | Returns JSON file |
| `/health` | GET | Health check | For monitoring services |

### API Examples

```bash
# Get recent releases
curl "https://your-app.ondigitalocean.app/api/films?status=released&limit=10"

# Search for Kurosawa films
curl "https://your-app.ondigitalocean.app/api/films?search=kurosawa"

# Get upcoming releases
curl "https://your-app.ondigitalocean.app/api/films?status=upcoming"

# Trigger scraping
curl -X POST "https://your-app.ondigitalocean.app/api/scrape"

# Get system statistics
curl "https://your-app.ondigitalocean.app/api/stats"
```

### Python API Client Example
```python
import requests

BASE_URL = "https://your-app.ondigitalocean.app"

# Get recent releases
response = requests.get(f"{BASE_URL}/api/films?status=released")
films = response.json()

for film in films[:5]:
    print(f"{film['title']} by {film['director']} ({film['release_date']})")

# Trigger update
requests.post(f"{BASE_URL}/api/scrape")
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_ENV` | Flask environment | `production` | No |
| `SECRET_KEY` | Flask secret key | - | Yes |
| `DATABASE_PATH` | SQLite database path | `/tmp/criterion_releases.db` | No |
| `PORT` | Server port | `8080` | No |

### Database Schema

The SQLite database contains a `films` table with these columns:

- `id` - Primary key
- `spine_number` - Criterion's unique spine number
- `title` - Film title
- `director` - Director name
- `release_date` - Release date (YYYY-MM-DD format)
- `release_status` - 'released' or 'upcoming'
- `format` - Format (Blu-ray, DVD, 4K, etc.)
- `price` - Price information
- `description` - Film description
- `url` - Link to film page on criterion.com
- `cover_art_url` - Cover art image URL
- `special_features` - Special features description
- `created_at` - Record creation timestamp
- `updated_at` - Last update timestamp

## 🚨 Troubleshooting

### Common Issues

**App won't start:**
- Check environment variables are set correctly
- Verify `SECRET_KEY` is provided
- Check DigitalOcean build logs

**No films showing:**
- Trigger a manual scrape via "Update Now" button
- Check status page for scraping errors
- Verify criterion.com is accessible

**Scraping fails:**
- Site structure may have changed
- Check logs in status page
- Rate limiting may be in effect

**Database errors:**
- Database file permissions (local dev)
- Disk space (DigitalOcean app platform uses temporary storage)

### Debugging

**Check application logs:**
1. Go to DigitalOcean Apps console
2. Select your app → Runtime Logs
3. Filter by component: `web`

**Manual scraping test:**
```bash
# SSH into droplet or use local development
python -c "
from criterion_scraper import CriterionScraper
scraper = CriterionScraper()
result = scraper.run_scraper()
print(f'Scraped {result} films')
"
```

**Database inspection:**
```python
import sqlite3
conn = sqlite3.connect('criterion_releases.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM films')
print(f"Total films: {cursor.fetchone()[0]}")
conn.close()
```

## 🔒 Privacy & Legal

- **Data Source**: All data scraped from publicly available criterion.com pages
- **Rate Limiting**: 2-second delays between requests to be respectful
- **Robots.txt Compliance**: Follows criterion.com/robots.txt guidelines
- **Usage**: Educational/personal use only
- **No Copyright Infringement**: Only metadata collected, no copyrighted content

## 📈 Performance & Scaling

### Current Limits
- **DigitalOcean Basic ($5/month)**: ~10,000 page views/month
- **Database**: SQLite (suitable for read-heavy workloads)
- **Scraping**: ~2-5 minutes per full scrape

### Scaling Options
- **Upgrade plan**: Professional ($12/month) for more traffic
- **Add database**: Managed PostgreSQL for persistence
- **Add caching**: Redis for improved performance
- **Load balancing**: Multiple app instances

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test locally: `python app.py`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature-name`
7. Create a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Add comments for complex logic
- Test changes locally before submitting
- Update documentation for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/tedrubin80/criterion-tracker/issues)
- **Documentation**: This README
- **API Reference**: Visit `/status` page on your deployed app

---

**Made with ❤️ for cinema lovers**

Deploy your own Criterion Collection tracker today and never miss a release!
