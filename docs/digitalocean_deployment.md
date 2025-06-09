# DigitalOcean App Platform Deployment

## 🚀 Quick Deployment (10 minutes!)

### Step 1: Prepare Your Code

Create these files in your project root:

#### `app.yaml`
```yaml
name: criterion-tracker
services:
- name: web
  source_dir: /
  github:
    repo: YOUR_USERNAME/criterion-tracker
    branch: main
  run_command: gunicorn --bind 0.0.0.0:8080 --timeout 120 app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
  routes:
  - path: /
  env:
  - key: FLASK_ENV
    value: production
  - key: SECRET_KEY
    value: your-super-secret-key-change-this
    type: SECRET
  - key: DATABASE_PATH
    value: /tmp/criterion_releases.db
```

#### `requirements.txt` (updated for App Platform)
```
Flask==2.3.3
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
gunicorn==21.2.0
python-dotenv==1.0.0
```

#### `runtime.txt`
```
python-3.11.4
```

#### Modify `app.py` for App Platform
```python
# Add this at the bottom of your app.py
if __name__ == '__main__':
    init_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

### Step 2: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/criterion-tracker.git
git push -u origin main
```

### Step 3: Deploy on DigitalOcean

1. **Login to DigitalOcean**
   - Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
   - Navigate to "Apps" in left sidebar

2. **Create New App**
   - Click "Create App"
   - Choose "GitHub" as source
   - Select your repository
   - Choose `main` branch

3. **Configure App**
   - DigitalOcean will auto-detect it's a Python app
   - Review the detected settings
   - Add environment variables:
     - `SECRET_KEY`: Generate a random string
     - `FLASK_ENV`: production

4. **Choose Plan**
   - **Basic ($5/month)**: Perfect for personal use
   - **Pro ($12/month)**: If you expect more traffic

5. **Deploy**
   - Click "Create Resources"
   - Wait 5-10 minutes for deployment
   - You'll get a URL like: `https://your-app-name.ondigitalocean.app`

### Step 4: Set Up Automated Scraping

#### Option A: Simple Cron Alternative
Add this to your Flask app to enable API-triggered scraping:

```python
# Add to app.py
import threading
import time
from datetime import datetime, timedelta

def scheduled_scraping():
    """Background thread for scheduled scraping"""
    while True:
        time.sleep(24 * 60 * 60)  # Wait 24 hours
        try:
            run_scraper_background()
        except Exception as e:
            logger.error(f"Scheduled scraping failed: {e}")

# Start background scheduler when app starts
if __name__ == '__main__' or __name__ == 'app':
    scheduler_thread = threading.Thread(target=scheduled_scraping, daemon=True)
    scheduler_thread.start()
```

#### Option B: External Cron Service
Use a service like [cron-job.org](https://cron-job.org) to hit your scraping endpoint:

- **URL to call:** `https://your-app.ondigitalocean.app/api/scrape`
- **Method:** POST
- **Schedule:** Daily at 9 AM
- **Free tier:** Available

### Step 5: Add Custom Domain (Optional)

1. **In DigitalOcean Apps Console:**
   - Go to your app → Settings → Domains
   - Add your custom domain

2. **Update DNS:**
   - Point your domain to the provided CNAME
   - SSL is automatic!

## 📊 Cost Breakdown

### Basic Plan ($5/month):
- 512 MB RAM
- 1 vCPU
- Perfect for personal use
- ~10,000 page views/month

### Professional Plan ($12/month):
- 1 GB RAM
- 1 vCPU
- Better for sharing/public use
- ~100,000 page views/month

## ✅ Advantages of App Platform

1. **Zero Server Management**
   - No SSH, no server updates
   - Automatic scaling
   - Built-in monitoring

2. **Automatic Deployments**
   - Push to GitHub = automatic deploy
   - Rollback capability
   - Zero downtime deployments

3. **Built-in Features**
   - Free SSL certificates
   - CDN included
   - Built-in monitoring/logs

4. **Python-Optimized**
   - Latest Python versions
   - Fast pip installs
   - Good performance

## 🛠️ Alternative: DigitalOcean Droplet

If you want more control (and slightly lower cost):

### $4/month Droplet Setup:
```bash
# 1. Create droplet (Ubuntu 22.04, $4/month)
# 2. SSH in and run:

# Install everything
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Clone your repo
git clone YOUR_REPO criterion-web
cd criterion-web

# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'
services:
  web:
    build: .
    ports:
      - "80:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=your-secret-key
    volumes:
      - ./data:/app/data
    restart: unless-stopped
EOF

# Deploy
docker-compose up -d
```

## 🔧 Monitoring & Maintenance

### View Logs:
```bash
# In DigitalOcean Apps console
Apps → Your App → Runtime Logs
```

### Update App:
```bash
# Just push to GitHub
git add .
git commit -m "Update"
git push

# App automatically redeploys!
```

### Scale Up:
- Go to Apps → Settings → Scale
- Increase instance size or count
- Changes apply immediately

## 🚨 Important Notes

1. **Database Storage:** App Platform uses temporary storage. For persistent data, consider adding a managed database later.

2. **Rate Limiting:** Be respectful with scraping frequency to avoid being blocked.

3. **Monitoring:** Set up alerts in DigitalOcean for uptime monitoring.

4. **Backups:** Regularly export your JSON data as backup.

This setup gives you a professional, scalable web application with minimal maintenance effort!
