# FILE: app.py
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

# Import the scraper (will be in same directory)
try:
    from criterion_scraper import CriterionScraper
except ImportError:
    # Fallback if scraper module not available
    CriterionScraper = None

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'criterion_releases.db')
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
    
    if CriterionScraper is None:
        logger.error("CriterionScraper not available")
        return False
    
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
        
        logger.info(f"Scraping