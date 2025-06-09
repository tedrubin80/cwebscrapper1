#!/usr/bin/env python3
"""
Criterion Collection Web Server
A Flask web application for scraping and displaying Criterion Collection releases
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

# Import the scraper
from criterion_scraper import CriterionScraper

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/tmp/criterion_releases.db')
SCRAPER_LOCK = threading.Lock()
SCRAPE_IN_PROGRESS = False

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingStatus:
    in_progress: bool = False
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    total_films: int = 0
    error_message: Optional[str] = None

scraping_status = ScrapingStatus()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_scraper_background():
    """Run scraper in background thread"""
    global scraping_status, SCRAPE_IN_PROGRESS
    
    with SCRAPER_LOCK:
        if SCRAPE_IN_PROGRESS:
            return False
        SCRAPE_IN_PROGRESS = True
    
    try:
        scraping_status.in_progress = True
        scraping_status.last_run = datetime.now()
        scraping_status.error_message = None
        
        logger.info("Starting background scraping task")
        scraper = CriterionScraper(DATABASE_PATH)
        scraper.run_scraper()
        
        # Update status
        conn = get_db_connection()
        total_films = conn.execute('SELECT COUNT(*) FROM films').fetchone()[0]
        conn.close()
        
        scraping_status.last_success = datetime.now()
        scraping_status.total_films = total_films
        scraping_status.error_message = None
        
        logger.info(f"Scraping completed successfully. Total films: {total_films}")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        scraping_status.error_message = str(e)
    
    finally:
        scraping_status.in_progress = False
        SCRAPE_IN_PROGRESS = False

# Auto-scraping scheduler
def scheduled_scraping():
    """Background thread for scheduled scraping every 24 hours"""
    while True:
        try:
            # Wait 24 hours
            time.sleep(24 * 60 * 60)
            logger.info("Starting scheduled scraping")
            run_scraper_background()
        except Exception as e:
            logger.error(f"Scheduled scraping failed: {e}")

# Start scheduler thread
scheduler_thread = threading.Thread(target=scheduled_scraping, daemon=True)
scheduler_thread.start()

@app.route('/')
def index():
    """Main dashboard"""
    conn = get_db_connection()
    
    # Get recent releases (last 30 days)
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    recent_releases = conn.execute('''
        SELECT * FROM films 
        WHERE release_status = 'released' 
        AND release_date >= ?
        ORDER BY release_date DESC
        LIMIT 10
    ''', (cutoff_date,)).fetchall()
    
    # Get upcoming releases
    today = datetime.now().strftime('%Y-%m-%d')
    upcoming_releases = conn.execute('''
        SELECT * FROM films 
        WHERE release_status = 'upcoming' 
        AND (release_date >= ? OR release_date IS NULL)
        ORDER BY release_date ASC
        LIMIT 10
    ''', (today,)).fetchall()
    
    # Get stats
    stats = {
        'total_films': conn.execute('SELECT COUNT(*) FROM films').fetchone()[0],
        'recent_count': conn.execute('''
            SELECT COUNT(*) FROM films 
            WHERE release_date >= ?
        ''', (cutoff_date,)).fetchone()[0],
        'upcoming_count': conn.execute('''
            SELECT COUNT(*) FROM films 
            WHERE release_status = 'upcoming'
        ''', ()).fetchone()[0]
    }
    
    conn.close()
    
    return render_template('index.html', 
                         recent_releases=recent_releases,
                         upcoming_releases=upcoming_releases,
                         stats=stats,
                         scraping_status=scraping_status)

@app.route('/all-releases')
def all_releases():
    """View all releases with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    
    # Build query
    where_clauses = []
    params = []
    
    if status_filter != 'all':
        where_clauses.append('release_status = ?')
        params.append(status_filter)
    
    if search:
        where_clauses.append('(title LIKE ? OR director LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    
    where_sql = ' AND '.join(where_clauses)
    if where_sql:
        where_sql = 'WHERE ' + where_sql
    
    # Get total count
    count_query = f'SELECT COUNT(*) FROM films {where_sql}'
    total = conn.execute(count_query, params).fetchone()[0]
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = f'''
        SELECT * FROM films {where_sql}
        ORDER BY release_date DESC, title ASC
        LIMIT ? OFFSET ?
    '''
    films = conn.execute(query, params + [per_page, offset]).fetchall()
    
    conn.close()
    
    # Pagination info
    total_pages = (total + per_page - 1) // per_page
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None
    }
    
    return render_template('all_releases.html', 
                         films=films,
                         pagination=pagination,
                         status_filter=status_filter,
                         search=search)

@app.route('/film/<int:film_id>')
def film_detail(film_id):
    """Individual film detail page"""
    conn = get_db_connection()
    film = conn.execute('SELECT * FROM films WHERE id = ?', (film_id,)).fetchone()
    conn.close()
    
    if not film:
        flash('Film not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('film_detail.html', film=film)

@app.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger scraping manually"""
    if scraping_status.in_progress:
        flash('Scraping is already in progress', 'warning')
        return redirect(url_for('index'))
    
    # Start scraping in background
    thread = threading.Thread(target=run_scraper_background, daemon=True)
    thread.start()
    
    flash('Scraping started in background', 'success')
    return redirect(url_for('index'))

@app.route('/status')
def scraping_status_page():
    """Detailed scraping status page"""
    return render_template('status.html', status=scraping_status)

# API Routes
@app.route('/api/films')
def api_films():
    """API endpoint for films"""
    status_filter = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search')
    
    conn = get_db_connection()
    
    where_clauses = []
    params = []
    
    if status_filter:
        where_clauses.append('release_status = ?')
        params.append(status_filter)
    
    if search:
        where_clauses.append('(title LIKE ? OR director LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    
    where_sql = ' AND '.join(where_clauses)
    if where_sql:
        where_sql = 'WHERE ' + where_sql
    
    query = f'''
        SELECT * FROM films {where_sql}
        ORDER BY release_date DESC
        LIMIT ?
    '''
    films = conn.execute(query, params + [limit]).fetchall()
    conn.close()
    
    return jsonify([dict(film) for film in films])

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    conn = get_db_connection()
    
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    stats = {
        'total_films': conn.execute('SELECT COUNT(*) FROM films').fetchone()[0],
        'recent_releases': conn.execute('''
            SELECT COUNT(*) FROM films 
            WHERE release_status = 'released' AND release_date >= ?
        ''', (cutoff_date,)).fetchone()[0],
        'upcoming_releases': conn.execute('''
            SELECT COUNT(*) FROM films 
            WHERE release_status = 'upcoming'
        ''').fetchone()[0],
        'last_scrape': scraping_status.last_run.isoformat() if scraping_status.last_run else None,
        'scraping_in_progress': scraping_status.in_progress
    }
    
    conn.close()
    return jsonify(stats)

@app.route('/api/scrape', methods=['POST'])
def api_trigger_scrape():
    """API endpoint to trigger scraping"""
    if scraping_status.in_progress:
        return jsonify({'error': 'Scraping already in progress'}), 400
    
    thread = threading.Thread(target=run_scraper_background, daemon=True)
    thread.start()
    
    return jsonify({'message': 'Scraping started'})

@app.route('/export')
def export_data():
    """Export all data as JSON"""
    conn = get_db_connection()
    films = conn.execute('SELECT * FROM films ORDER BY release_date DESC').fetchall()
    conn.close()
    
    data = {
        'exported_at': datetime.now().isoformat(),
        'total_films': len(films),
        'films': [dict(film) for film in films]
    }
    
    response = app.response_class(
        response=json.dumps(data, indent=2, default=str),
        status=200,
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = 'attachment; filename=criterion_releases.json'
    return response

# Health check endpoint for DigitalOcean
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Initialize database on startup
def init_app():
    """Initialize the application"""
    if not os.path.exists(DATABASE_PATH):
        scraper = CriterionScraper(DATABASE_PATH)
        logger.info("Database initialized")
    
    # Get current status
    try:
        conn = get_db_connection()
        scraping_status.total_films = conn.execute('SELECT COUNT(*) FROM films').fetchone()[0]
        conn.close()
    except:
        scraping_status.total_films = 0

# Template functions
@app.template_filter('datetime')
def datetime_filter(value):
    """Format datetime for templates"""
    if value is None:
        return 'N/A'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return value
    return value.strftime('%Y-%m-%d %H:%M')

@app.template_filter('date')
def date_filter(value):
    """Format date for templates"""
    if value is None:
        return 'TBA'
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except:
            return value
    return value.strftime('%B %d, %Y')

# Initialize app
init_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
