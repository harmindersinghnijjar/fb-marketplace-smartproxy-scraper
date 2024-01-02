"""Python script to scrape Facebook Marketplace listings in a given Canadian city for a given vehicle and upload them to a SQL database."""

import asyncio
from email.mime import image
import json
from math import log
import re
import urllib.parse
import webbrowser
import requests
from bs4 import BeautifulSoup
import logging
import time
import sqlite3
from datetime import datetime, timedelta
import os.path
import os
import os.path
import pickle

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("fb-marketplace-smartproxy-scraper.log")
log_format = logging.Formatter(
    "%(asctime)s - %(name)s - [%(levelname)s] [%(pathname)s:%(lineno)d] - %(message)s - [%(process)d:%(thread)d]"
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('market_listings.db')
        self.cursor = self.conn.cursor()
        self._prepare_database()

    def _prepare_database(self):
        """Create the database table if it does not exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                mileage REAL,
                price REAL NOT NULL,
                location TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        
    def listing_exists(self, url):
        self.cursor.execute("SELECT COUNT(1) FROM market_listings WHERE url = ?", (url,))
        return self.cursor.fetchone()[0] > 0

    def create_market_listing(self, title, mileage, price, location, url, image):
        if self.listing_exists(url):
            logger.info(f"Listing with URL {url} already exists. Skipping insert.")
            return None
        try:
            self.cursor.execute('''
                INSERT INTO market_listings (title, mileage, price, location, url, image)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, mileage, price, location, url, image))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"Unique constraint failed while inserting into database: {e}")
            return None
        except Exception as e:
            logger.error(f"An error occurred while inserting into database: {e}")
            return None

    def retrieve_all_listings(self):
        self.cursor.execute("SELECT * FROM market_listings")
        return self.cursor.fetchall()

    def close_connection(self):
        self.conn.close()


class FacebookMarketplaceScraper:
    def __init__(self, city, query, db_manager):
        self.city = city
        self.query = query
        self.db_manager = db_manager

    def scrape_city(self, city, query):
        """Scrape a single city."""
        url = "https://scraper-api.smartproxy.com/v2/scrape"
        logger.info(f"Scraping {city}.")
        payload = {
            "target": "universal",
            "locale": "en-US",
            "device_type": "desktop",
            "headless": "html",
            "url": f"https://www.facebook.com/marketplace/{city}/search/?query={query}&exact=false",
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": "YOUR_API_KEY",
        }
  
        logger.info(f"payload: {payload}")
        logger.info(f"headers: {headers}")

        response = requests.post(url, data=json.dumps(payload), headers=headers)

        # Get the enitre response
        logger.info(f"response.text: {response.text}")
        logger.info(f"response.status_code: {response.status_code}")

        # Get the JSON response
        json_response = response.json()

        if response.content == "null":
            logger.error(
                f"Error while scraping: {response.status_code}, {response.text}"
            )
            return []

        try:
            json_response = response.json()
        except ValueError as e:
            logger.error(f"Error decoding JSON: {e}")
            return []

        listings_content = json_response.get("results", [])
        if not listings_content:
            logger.info("No results found in the response.")
            return []

        first_result_content = listings_content[0].get("content")
        if not first_result_content:
            logger.info("No content found in the first result.")
            return []

        soup = BeautifulSoup(first_result_content, "html.parser")
        soup_listings = soup.find_all(
            "div",
            class_="x9f619 x78zum5 x1r8uery xdt5ytf x1iyjqo2 xs83m0k x1e558r4 x150jy0e x1iorvi4 xjkvuk6 xnpuxes x291uyu x1uepa24",
        )

        if not soup_listings:
            logger.info("No listings found in the parsed HTML.")
            return []

        logger.info(f"Found {len(soup_listings)} listings.")
        return soup_listings

    def parse_listings(self, soup_listings):
        new_listings = []  # Initialize an empty list to collect new listings
        for soup_listing in soup_listings:
            # Extract data from each listing
            try:
                # Extract price using regex
                price = self.extract_price(soup_listing)

                # Extract mileage using regex
                mileage = self.extract_mileage(soup_listing)

                # Extract title
                title = self.extract_title(soup_listing)

                # Extract image URL
                image = self.extract_image(soup_listing)

                # Extract location
                location = self.extract_location(soup_listing)

                # Extract post URL
                post_url = self.extract_post_url(soup_listing)

                # Validate extracted data
                if not self.is_valid_listing(title, price, location, post_url):
                    continue

                # Check if the listing already exists in the database
                if self.db_manager.listing_exists(post_url):
                    continue

                # Add new listing to the database
                listing_id = self.db_manager.create_market_listing(
                    title, mileage, price, location, post_url, image
                )
                if listing_id:
                    new_listings.append(
                        (title, mileage, price, location, post_url, image)
                    )
            except Exception as e:
                logger.error(f"Error processing listing: {e}")
                continue
        logger.info(f"Found {len(new_listings)} new listings.")
        return new_listings

    def extract_price(self, soup_listing):
        text = soup_listing.get_text(strip=True)

        # Match prices potentially followed by a year in the range 1950-2024
        price_match = re.search(r"(\$\d{1,3}(?:,\d{3})?)(?=(1950|19[6-9]\d|20[0-1]\d|202[0-4])?)", text)
        if price_match:
            return price_match.group(1)

        # If the above pattern does not match, fall back to the original patterns
        # Canadian dollar sign, without year
        price_match = re.search(r"(\$\d+,\d+)", text)
        if price_match:
            return price_match.group(1)

        # US dollar sign, without year
        price_match = re.search(r"(\$\d+)", text)
        if price_match:
            return price_match.group(1)

        return None

    def extract_mileage(self, soup_listing):
        mileage_match = re.search(r"(\d+K) km", soup_listing.get_text(strip=True))
        return mileage_match.group(1) if mileage_match else None

    def extract_title(self, soup_listing):
        title_elem = soup_listing.find(
            "span", class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6"
        )
        return title_elem.get_text(strip=True) if title_elem else None

    def extract_image(self, soup_listing):
        image_elem = soup_listing.find(
            "img", class_="xt7dq6l xl1xv1r x6ikm8r x10wlt62 xh8yej3"
        )
        return image_elem["src"] if image_elem else None

    def extract_location(self, soup_listing):
        # Extract location in the form of an Uppercase followed by Lowercase letters until a comma is found and than two uppercase letters
        location_match = re.search(
            r"([A-Z][a-z]+(?: [A-Z][a-z]+)*), [A-Z]{2}",
            soup_listing.get_text(strip=True),
        )
        location = location_match.group(1) if location_match else None
        return location

    def extract_post_url(self, soup_listing):
        url_elem = soup_listing.find(
            "a",
            class_="x1i10hfl xjbqb8w x6umtig x1b1mbwd xaqea5y xav7gou x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g x1lku1pv",
        )
        return "https://www.facebook.com" + url_elem["href"] if url_elem else None

    def is_valid_listing(self, title, price, location, url):
        # Log why a listing is invalid if it is
        if not title or not price or not location or not url:
            missing_info = []
            if not title:
                missing_info.append("title")
            if not price:
                missing_info.append("price")
            if not location:
                missing_info.append("location")
            if not url:
                missing_info.append("url")
            # If all four are missing, go to the next listing without logging
            if len(missing_info) == 4:
                pass
        # Check if the listing is valid
        is_valid = title and price and location and url
        if not is_valid:
            pass
        return is_valid

    async def scrape_city_and_save_periodically(self, city, query, interval, duration):
     
        start_time = datetime.now()
        logger.info(f"Starting periodic scraping at {start_time}.")
        end_time = start_time + timedelta(hours=duration)
        logger.info(f"Periodic scraping will end at {end_time}.")

        while datetime.now() < end_time:
            try:
                # Scrape the city
                soup_listings = self.scrape_city(city, query)
                logger.info(f"Scraped {city} at {datetime.now()}.")
                logger.info(f"Scraped {len(soup_listings)} listings.")
                if not soup_listings:
                    logger.info("No listings found to process.")
                    continue

                # Parse the listings
                new_listings = self.parse_listings(soup_listings)
                if not new_listings:
                    logger.info("No new listings found to upload.")
                    continue

                logger.info(f"Found {len(new_listings)} new listings.")
                logger.info(f"new_listings: {new_listings}")

                # Upload the listings to SQL database
                for new_listing in new_listings:
                    title, mileage, price, location, url, image = new_listing
                    # Upload the listing to the database
                    listing_id = self.db_manager.create_market_listing(
                        title, mileage, price, location, url, image
                    )
                    if listing_id:
                        logger.info(f"Uploaded listing {listing_id} to database.")
                    else:
                        logger.error(f"Failed to upload listing {listing_id} to database.")
            except Exception as e:
                logger.error(f"Error while scraping: {e}")
                continue
            finally:
                # Wait for the specified interval
                await asyncio.sleep(interval)


if __name__ == "__main__":
    # Initialize the database manager
    db_manager = DatabaseManager()


    # Initialize the scraper to scrape Toronto for BMWs
    scraper = FacebookMarketplaceScraper("toronto", "bmw", db_manager)

    # Scrape   Toronto for BMWs every 5 minutes for 1 hour
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        scraper.scrape_city_and_save_periodically("toronto", "bmw", 300, 1)
    )



                