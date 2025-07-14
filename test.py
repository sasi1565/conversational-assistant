# import requests
# from bs4 import BeautifulSoup
# import re
# import random


# # def check_price_changes(product_url):
# #     """Check current price and name of a product from its URL"""
# #     try:
# #         # Set headers to mimic a browser request
# #         headers = {
# #             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
# #         }

# #         # Get the webpage content
# #         response = requests.get(product_url, headers=headers)
# #         response.raise_for_status()  # Raise exception for bad status codes
# #         soup = BeautifulSoup(response.content, 'html.parser')

# #         # Define selectors for different e-commerce sites
# #         selectors = {
# #             'amazon': {
# #                 'price_selector': 'span.a-price-whole',
# #                 'name_selector': 'span#productTitle',
# #                 'currency': '₹'
# #             },
# #             'flipkart': {
# #                 'price_selector': 'div.Nx9bqj',
# #                 'name_selector': 'span.VU-ZEz',
# #                 'currency': '₹'
# #             },
# #         }

# #         # Determine which website we're scraping
# #         website = None
# #         if 'amazon.' in product_url:
# #             website = 'amazon'
# #         elif 'flipkart.' in product_url:
# #             website = 'flipkart'

# #         if not website:
# #             return None

# #         # Extract product name
# #         product_name = soup.select_one(selectors[website]['name_selector'])
# #         product_name = product_name.get_text().strip() if product_name else "Unknown Product"

# #         # Extract price
# #         price_element = soup.select_one(selectors[website]['price_selector'])
# #         price_text = price_element.get_text().strip() if price_element else None

# #         # Clean price text
# #         print(price_text)
# #         price = re.sub(r"[^\d.]", "", price_text) if price_text else None


# #         # Return extracted details
# #         return {
# #             "product_name": product_name,
# #             "price": float(price) if price else None,
# #             "currency": selectors[website]['currency'],
# #             "website": website,
# #             "url": product_url
# #         }

# #     except Exception as e:
# #         print(f"Error checking price: {e}")
# #         return None

# from playwright.sync_api import sync_playwright
# import re

# def check_price_changes(product_url):
#     """Check current price and product details using Playwright."""
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page()
#         page.goto(product_url, timeout=60000)  # Wait for page to fully load

#         # Define selectors
#         selectors = {
#             'amazon': {
#                 'price_selector': 'span.a-price-whole',
#                 'name_selector': 'span#productTitle',
#                 'currency': '₹'
#             },
#             'flipkart': {
#                 'price_selector': 'div._30jeq3._16Jk6d',  # Updated Flipkart price selector
#                 'name_selector': 'span.B_NuCI',  # Updated Flipkart product name selector
#                 'currency': '₹'
#             },
#         }

#         # Determine website
#         website = None
#         if "amazon." in product_url:
#             website = "amazon"
#         elif "flipkart." in product_url:
#             website = "flipkart"
#         else:
#             return None

#         # Wait for product name to appear
#         page.wait_for_selector(selectors[website]["name_selector"], timeout=10000)
#         product_name = page.locator(selectors[website]["name_selector"]).text_content().strip()

#         # Wait for price to appear
#         page.wait_for_selector(selectors[website]["price_selector"], timeout=10000)
#         price_text = page.locator(selectors[website]["price_selector"]).text_content().strip()

#         # Extract numerical price
#         price = re.sub(r"[^\d.]", "", price_text) if price_text else None

#         browser.close()

#         return {
#             "product_name": product_name,
#             "price": float(price) if price else None,
#             "currency": selectors[website]['currency'],
#             "website": website,
#             "url": product_url
#         }

# # Example usage
# print(check_price_changes("https://www.flipkart.com/vivo-t4x-5g-marine-blue-128-gb/p/itm017656bdd097b"))


# # print(check_price_changes("https://www.flipkart.com/vivo-t4x-5g-marine-blue-128-gb/p/itm017656bdd097b?pid=MOBH9JUSTWEMVADU&lid=LSTMOBH9JUSTWEMVADU5W2ENU&marketplace=FLIPKART&fm=productRecommendation%2Fsimilar&iid=en_S0FWn_-GNSzoVZn5VChvVR5-in-LO8JhXEkavECaRaZYI1P9cqul8jZMFQPQoi-w8nn_tfi0F7ZqGzdcZ60oMg%3D%3D&ppt=pp&ppn=pp&ssid=e9556056o00000001742194949972&otracker=pp_reco_Similar%2BProducts_2_37.productCard.PMU_HORIZONTAL_vivo%2BT4x%2B5G%2B%2528Marine%2BBlue%252C%2B128%2BGB%2529_-1_productRecommendation%2Fsimilar_1&otracker1=pp_reco_PINNED_productRecommendation%2Fsimilar_Similar%2BProducts_GRID_productCard_cc_2_NA_view-all&cid=-1"))

import requests
from bs4 import BeautifulSoup
import smtplib
import sqlite3
import time
from email.message import EmailMessage
import os
from datetime import datetime

# Configuration
DATABASE_NAME = "price_tracker.db"
CHECK_INTERVAL = 120  # 2 minutes in seconds
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Email Configuration (REPLACE WITH YOUR VALUES)
YOUR_EMAIL = "sasikiran1565@gmail.com"  # Replace with your email
YOUR_PASSWORD = "sasi@1234"  # Replace with app password
TEST_RECIPIENT = YOUR_EMAIL  # Send test emails to yourself

def initialize_database():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 url TEXT UNIQUE,
                 current_price REAL,
                 user_email TEXT,
                 product_name TEXT,
                 last_checked TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_product(url, user_email):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    price, product_name = get_product_info(url)
    
    if price:
        c.execute('''INSERT INTO products 
                     (url, current_price, user_email, product_name, last_checked)
                     VALUES (?, ?, ?, ?, ?)''',
                 (url, price, user_email, product_name, datetime.now()))
        conn.commit()
        print(f"✅ Product added!\nName: {product_name}\nInitial Price: ${price}")
    else:
        print("❌ Failed to retrieve product info")
    
    conn.close()

def get_product_info(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Simulated price for testing (remove in production)
        # price = 100.00  # Uncomment to force test price
        # product_name = "Test Product"
        
        # Real parsing (Amazon)
        if 'amazon' in url:
            price_whole = soup.find('span', class_='a-price-whole')
            price_fraction = soup.find('span', class_='a-price-fraction')
            if price_whole and price_fraction:
                price = float(price_whole.get_text().replace(',', '')) + float(price_fraction.get_text())/100
            else:
                price_element = soup.find('span', {'id': 'priceblock_ourprice'})
                if price_element:
                    price = float(price_element.get_text().replace('$', '').replace(',', ''))
                else:
                    return None, None
            
            product_name = soup.find('span', {'id': 'productTitle'}).get_text().strip()
            return price, product_name
        
        return None, None
    
    except Exception as e:
        print(f"⚠️ Error fetching product info: {e}")
        return None, None

def send_email(recipient, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = YOUR_EMAIL
    msg['To'] = recipient
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(YOUR_EMAIL, YOUR_PASSWORD)
            server.send_message(msg)
            print(f"📧 Email sent to {recipient}")
            print(f"   Subject: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def check_price_changes():
    print(f"\n=== Checking Prices at {datetime.now().strftime('%H:%M:%S')} ===")
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM products')
    products = c.fetchall()
    
    for product in products:
        product_id, url, old_price, user_email, product_name, last_checked = product
        print(f"\n🔍 Checking: {product_name}")
        print(f"   URL: {url}")
        print(f"   Last Price: ${old_price}")
        
        new_price, _ = get_product_info(url)
        
        if new_price:
            print(f"   Current Price: ${new_price}")
            
            if new_price != old_price:
                # Update database
                c.execute('''UPDATE products 
                             SET current_price = ?, last_checked = ?
                             WHERE id = ?''', 
                          (new_price, datetime.now(), product_id))
                conn.commit()
                
                # Send notification
                if new_price < old_price:
                    subject = f"🚨 Price Drop: {product_name}"
                    change = f"↓ ${old_price - new_price:.2f}"
                else:
                    subject = f"⚠️ Price Increase: {product_name}"
                    change = f"↑ ${new_price - old_price:.2f}"
                
                body = f"""Price Change Alert!

Product: {product_name}
Change: {change}
Old Price: ${old_price:.2f}
New Price: ${new_price:.2f}

Check it out: {url}
"""
                send_email(user_email, subject, body)
            else:
                print("   No price change detected")
        else:
            print("   ❗ Failed to get current price")
    
    conn.close()

def main():
    initialize_database()
    print("\n" + "="*50)
    print("Price Tracker Running")
    print(f"Check interval: {CHECK_INTERVAL//60} minutes")
    print(f"Tracking emails will be sent from: {YOUR_EMAIL}")
    print("="*50 + "\n")
    
    try:
        while True:
            check_price_changes()
            print(f"\n⏳ Next check at {(datetime.now().timestamp() + CHECK_INTERVAL):.0f}")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Tracker stopped by user")

if __name__ == "__main__":
    # Add a test product (uncomment to use)
    add_product("https://www.amazon.in/OnePlus-Misty-Green-128GB-Storage/dp/B0C7V7VH6Q", TEST_RECIPIENT)
    
    main()