import os
import json
import csv
import re
from datetime import datetime

# --- KHU VỰC IMPORT ---
# 1. 'cffi' để giả lập trình duyệt (Scraping)
from curl_cffi import requests as cffi 
# 2. 'requests' thường để gửi API Telegram (Gửi ảnh)
import requests 
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load cấu hình
load_dotenv()
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- CẤU HÌNH ---
HISTORY_FILE = 'price_history.json'
LOG_FILE = 'price_log.csv'
TARGET_URL = "https://sonpixel.vn/danh-muc-san-pham/dien-thoai/google-pixel/pixel-9-series/pixel-9/"
TARGET_PRICE = 10900000 
IMG_FILE = 'price_chart.png'

def send_telegram_photo(caption):
    """Gửi ảnh qua Telegram dùng thư viện requests thường"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    try:
        with open(IMG_FILE, 'rb') as photo:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            files = {'photo': photo}
            requests.post(url, data=payload, files=files, timeout=20)
            print("   >>> 📸 Đã gửi biểu đồ qua Telegram!")
    except Exception as e:
        print(f"Lỗi gửi ảnh: {e}")

def send_telegram_text(message):
    """Gửi text qua Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi tin nhắn: {e}")

def clean_price(price_str):
    if not price_str: return 0
    digits = re.sub(r'\D', '', price_str)
    return int(digits) if digits else 0

def log_to_csv(title, price):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(['Date', 'Product', 'Price'])
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([now, title, price])

def draw_chart():
    try:
        if not os.path.exists(LOG_FILE): return False
        
        df = pd.read_csv(LOG_FILE)
        df['Date'] = pd.to_datetime(df['Date'])
        
        plt.figure(figsize=(10, 5))
        
        for product_name in df['Product'].unique():
            subset = df[df['Product'] == product_name].sort_values('Date')
            if len(subset) > 0:
                plt.plot(subset['Date'], subset['Price'], marker='o', label=product_name)

        plt.title('Biến động giá Pixel 9 (SonPixel)')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize='small')
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        plt.gcf().autofmt_xdate()
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        plt.tight_layout()
        plt.savefig(IMG_FILE)
        plt.close()
        return True
    except Exception as e:
        print(f"Lỗi vẽ biểu đồ: {e}")
        return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=2)

def main():
    print(f"🚀 Đang chạy SonPixel Scraper (Clean Mode)...")
    
    # --- 1. VƯỢT TƯỜNG LỬA (ROTATION STRATEGY) ---
    browsers = ["chrome110", "edge101", "safari15_5"]
    response = None
    
    for browser in browsers:
        print(f"   🎭 Đang thử giả dạng: {browser}...")
        try:
            response = cffi.get(
                TARGET_URL, 
                impersonate=browser, 
                headers={"Referer": "https://www.google.com/"},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"   ✅ Thành công với: {browser}")
                break 
            elif response.status_code == 403:
                print(f"   ❌ {browser} bị chặn (403).")
            else:
                print(f"   ⚠️ Lỗi khác: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Lỗi kết nối khi thử {browser}: {e}")

    if not response or response.status_code != 200:
        print("❌ TẤT CẢ ĐỀU THẤT BẠI. IP của bạn có thể đã bị chặn tạm thời.")
        return

    # --- 2. XỬ LÝ DỮ LIỆU ---
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        products = soup.select('.product-small')
        print(f"🔎 Tìm thấy {len(products)} thành phần HTML (chưa lọc).")
        
        history = load_history()
        deal_info = []
        
        # --- FIX: Tạo set để lọc trùng lặp ---
        seen_titles = set()

        for product in products:
            try:
                title_el = product.select_one('.woocommerce-loop-product__title')
                if not title_el: continue
                title = title_el.get_text().strip()

                # --- BƯỚC LỌC TRÙNG ---
                if title in seen_titles:
                    continue # Nếu đã gặp tên này rồi thì bỏ qua ngay
                seen_titles.add(title) # Đánh dấu là đã gặp

                # --- BỘ LỌC TỪ KHÓA ---
                if "Pixel 9" not in title or "Pro" in title or "Lock" in title: continue

                # --- LẤY GIÁ ---
                price_el = product.select_one('.price .woocommerce-Price-amount bdi') or product.select_one('.price')
                price = clean_price(price_el.get_text() if price_el else "0")

                if price > 0:
                    log_to_csv(title, price)
                    print(f"   ✅ {title}: {price:,} đ")

                # --- LOGIC ALERT ---
                if 5000000 < price < TARGET_PRICE:
                    last_price = history.get(title, 99999999)
                    if price < last_price:
                        deal_info.append(f"📱 **{title}**: {price:,}đ (Giảm từ {last_price:,}đ)")
                
                history[title] = price
            except: continue

        save_history(history)

        # Gửi báo cáo
        if deal_info:
            print("🔥 Phát hiện Deal! Đang xử lý báo cáo...")
            has_chart = draw_chart()
            caption = "🚨 **PHÁT HIỆN GIÁ GIẢM!**\n\n" + "\n".join(deal_info) + f"\n\n👉 [Xem ngay]({TARGET_URL})"
            
            if has_chart:
                send_telegram_photo(caption)
            else:
                send_telegram_text(caption)

        print("✅ Hoàn tất.")

    except Exception as e:
        print(f"❌ Lỗi xử lý HTML: {e}")

if __name__ == "__main__":
    main()