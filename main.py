import requests
from bs4 import BeautifulSoup
import os
import json
import re

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
HISTORY_FILE = 'price_history.json'
TARGET_URL = "https://sonpixel.vn/danh-muc-san-pham/dien-thoai/google-pixel/pixel-9-series/pixel-9/"
TARGET_PRICE = 10900000  # Alert if price < 10.9 Million

# --- PASTE HEADERS HERE ---
# Copy the User-Agent and Cookie from your Network Tab (HAR)
# This is critical to look like a real browser.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    # 'Cookie': 'PASTE_YOUR_COOKIE_STRING_HERE_IF_NEEDED' 
}

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("!! Telegram tokens not found in ENV")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

def clean_price(price_str):
    if not price_str: return 0
    # Remove dots, 'd', 'VND', and whitespace
    digits = re.sub(r'\D', '', price_str)
    return int(digits) if digits else 0

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def main():
    print(f"🚀 Starting SonPixel Scraper for Pixel 9...")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        response = session.get(TARGET_URL, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Network Error: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Select all product cards in the grid
    products = soup.select('.product-small')
    print(f"🔎 Found {len(products)} products on page.")

    history = load_history()
    deals_found = False

    for product in products:
        try:
            # Extract Title
            title_el = product.select_one('.woocommerce-loop-product__title')
            if not title_el: continue
            title = title_el.get_text().strip()

            # Filter: STRICTLY Pixel 9 (No Pro, No Lock if desired)
            if "Pixel 9" not in title:
                continue
            if "Pro" in title: # Skip Pro models
                continue
            if "Lock" in title: # User Requirement: Banking apps need clean machine
                print(f"   Skip (Lock): {title}")
                continue

            # Extract Price
            # Looks for <span class="woocommerce-Price-amount amount"><bdi>14.490.000...
            price_el = product.select_one('.price .woocommerce-Price-amount bdi')
            if not price_el:
                # Sometimes it's a range, just grab the first text
                price_el = product.select_one('.price')
            
            raw_price = price_el.get_text() if price_el else "0"
            price = clean_price(raw_price)

            print(f"   Checked: {title} - {price:,} VND")

            # --- LOGIC: DEAL DETECTION ---
            # 1. Price is valid (> 5M) and Cheap (< TARGET)
            if 5000000 < price < TARGET_PRICE:
                last_seen_price = history.get(title, 99999999)
                
                # Only alert if price dropped OR it's the first time seeing this deal
                if price < last_seen_price:
                    msg = (
                        f"🔥 **DEAL ALERT: SonPixel**\n"
                        f"📦 **{title}**\n"
                        f"💰 **{price:,} VND**\n"
                        f"📉 (Old: {last_seen_price:,} VND)\n"
                        f"👉 [Buy Now]({TARGET_URL})"
                    )
                    send_telegram(msg)
                    print(f"   >>> ALERT SENT for {title}")
                    deals_found = True
            
            # Update history regardless to keep state fresh
            history[title] = price

        except Exception as e:
            print(f"Error parsing item: {e}")

    save_history(history)
    print("✅ Done.")

if __name__ == "__main__":
    main()