#!/usr/bin/env python3
"""
Criterion Collection Release Scraper
Optimized for web deployment and DigitalOcean App Platform
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
from datetime import datetime
import logging
from typing import List, Dict, Optional

class CriterionScraper:
    def __init__(self, db_path: str = "/tmp/criterion_releases.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Criterion Collection Release Tracker Bot 1.0 (Educational/Personal Use)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.init_database()
        
        # URLs to scrape
        self.urls = {
            'new_releases': 'https://www.criterion.com/shop/browse?popular=new-releases',
            'coming_soon': 'https://www.criterion.com/shop/browse?popular=coming-soon'
        }
    
    def init_database(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS films (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spine_number TEXT UNIQUE,
                title TEXT NOT NULL,
                director TEXT,
                release_date DATE,
                release_status TEXT,
                format TEXT,
                price TEXT,
                description TEXT,
                url TEXT,
                cover_art_url TEXT,
                special_features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_release_date ON films(release_date);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_release_status ON films(release_status);
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Database initialized successfully")
    
    def rate_limit(self, delay: float = 2.0):
        """Respectful rate limiting between requests"""
        time.sleep(delay)
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def parse_release_date(self, date_text: str) -> Optional[str]:
        """Parse release date from various formats"""
        if not date_text:
            return None
            
        # Patterns for different date formats
        patterns = [
            r'Released\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'Available\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse the date
                    for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%B %d %Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except Exception as e:
                    self.logger.warning(f"Error parsing date '{date_text}': {e}")
        
        return None
    
    def extract_spine_number(self, text: str) -> Optional[str]:
        """Extract Criterion spine number from text"""
        spine_match = re.search(r'#(\d+)', text)
        if spine_match:
            return spine_match.group(1)
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.split()).strip()
    
    def scrape_releases_page(self, url: str, status: str) -> List[Dict]:
        """Scrape a releases page and extract film data"""
        soup = self.fetch_page(url)
        if not soup:
            return []
        
        films = []
        
        # Look for film items in the page
        # Criterion's site structure as of 2024/2025
        film_containers = soup.find_all(['div', 'article'], class_=re.compile(r'product|item|film'))
        
        if not film_containers:
            # Fallback: look for any links that contain film URLs
            film_links = soup.find_all('a', href=re.compile(r'/films/|/shop/product/'))
            film_containers = [link.find_parent() for link in film_links if link.find_parent()]
        
        self.logger.info(f"Found {len(film_containers)} potential film containers")
        
        for container in film_containers:
            try:
                film_data = self.extract_film_data(container, status)
                if film_data:
                    films.append(film_data)
                    self.logger.info(f"Extracted: {film_data.get('title', 'Unknown')}")
            except Exception as e:
                self.logger.warning(f"Error extracting film data: {e}")
                continue
        
        self.logger.info(f"Successfully extracted {len(films)} films from {url}")
        return films
    
    def extract_film_data(self, container, status: str) -> Optional[Dict]:
        """Extract film data from a container element"""
        data = {'release_status': status}
        
        # Get all text content for processing
        full_text = container.get_text()
        
        # Find title - usually in h2, h3, or strong tag, or as link text
        title_elem = (container.find(['h1', 'h2', 'h3', 'h4']) or 
                     container.find('strong') or 
                     container.find('a', href=re.compile(r'/films/|/shop/product/')))
        
        if title_elem:
            title = self.clean_text(title_elem.get_text())
            # Filter out non-title text
            if title and len(title) > 2 and not re.match(r'^(Quick Shop|Buy Now|View|Released|Available)$', title):
                data['title'] = title
        
        # Extract director - usually follows title or is in smaller text
        director_candidates = container.find_all(['p', 'div', 'span'], string=re.compile(r'^[A-Z][a-z]+ [A-Z]'))
        for candidate in director_candidates:
            text = self.clean_text(candidate.get_text())
            # Simple heuristic: director names are usually 2-4 words, no numbers
            if text and 2 <= len(text.split()) <= 4 and not re.search(r'\d|Released|Available|Quick', text):
                data['director'] = text
                break
        
        # Extract release date
        date_match = re.search(r'(Released|Available)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', full_text)
        if date_match:
            date_str = date_match.group(2)
            data['release_date'] = self.parse_release_date(date_str)
        
        # Extract spine number
        spine_match = re.search(r'#(\d+)', full_text)
        if spine_match:
            data['spine_number'] = spine_match.group(1)
        
        # Extract format
        format_match = re.search(r'(Blu-ray|DVD|4K|Collector\'s Set)', full_text)
        if format_match:
            data['format'] = format_match.group(1)
        
        # Find cover image
        img = container.find('img')
        if img and img.get('src'):
            src = img.get('src')
            if src.startswith('http'):
                data['cover_art_url'] = src
            elif src.startswith('/'):
                data['cover_art_url'] = 'https://www.criterion.com' + src
        
        # Find product URL
        link = container.find('a', href=re.compile(r'/films/|/shop/product/'))
        if link and link.get('href'):
            href = link.get('href')
            if href.startswith('/'):
                data['url'] = 'https://www.criterion.com' + href
            else:
                data['url'] = href
        
        # Only return if we have at least a title
        if data.get('title'):
            return data
        
        return None
    
    def save_to_database(self, films: List[Dict]):
        """Save film data to database"""
        if not films:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        updated_count = 0
        
        for film in films:
            try:
                # Check if film already exists (by title and director)
                cursor.execute('''
                    SELECT id FROM films 
                    WHERE title = ? AND COALESCE(director, '') = COALESCE(?, '')
                ''', (film.get('title'), film.get('director')))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE films SET
                            spine_number = COALESCE(?, spine_number),
                            release_date = COALESCE(?, release_date),
                            release_status = COALESCE(?, release_status),
                            format = COALESCE(?, format),
                            price = COALESCE(?, price),
                            description = COALESCE(?, description),
                            url = COALESCE(?, url),
                            cover_art_url = COALESCE(?, cover_art_url),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        film.get('spine_number'),
                        film.get('release_date'),
                        film.get('release_status'),
                        film.get('format'),
                        film.get('price'),
                        film.get('description'),
                        film.get('url'),
                        film.get('cover_art_url'),
                        existing[0]
                    ))
                    updated_count += 1
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO films (
                            spine_number, title, director, release_date, 
                            release_status, format, price, description, 
                            url, cover_art_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        film.get('spine_number'),
                        film.get('title'),
                        film.get('director'),
                        film.get('release_date'),
                        film.get('release_status'),
                        film.get('format'),
                        film.get('price'),
                        film.get('description'),
                        film.get('url'),
                        film.get('cover_art_url')
                    ))
                    saved_count += 1
                    
            except sqlite3.Error as e:
                self.logger.error(f"Database error for {film.get('title')}: {e}")
        
        conn.commit()
        conn.close()
        self.logger.info(f"Database updated: {saved_count} new, {updated_count} updated")
    
    def run_scraper(self):
        """Main scraper execution"""
        self.logger.info("Starting Criterion Collection scraper")
        all_films = []
        
        for page_name, url in self.urls.items():
            status = 'released' if 'new-releases' in url else 'upcoming'
            
            self.logger.info(f"Scraping {page_name}: {url}")
            films = self.scrape_releases_page(url, status)
            all_films.extend(films)
            
            # Rate limit between pages
            self.rate_limit()
        
        if all_films:
            self.save_to_database(all_films)
            self.logger.info(f"Scraping completed. Total films processed: {len(all_films)}")
        else:
            self.logger.warning("No films were scraped. Check site structure or selectors.")
        
        return len(all_films)

if __name__ == "__main__":
    # For testing
    scraper = CriterionScraper()
    scraper.run_scraper()
