# Project: SonPixel "Grid Hunter" (Category Scraper)

## 1. Project Overview
A Python script running on GitHub Actions to monitor the **Pixel 9 Category Page** on SonPixel.vn. It iterates through the product grid to find the best deal for "Pixel 9 Quốc Tế" (ignoring "Lock" or "Pro" if needed).

## 2. Input Data
* **Target URL:** `https://sonpixel.vn/danh-muc-san-pham/dien-thoai/google-pixel/pixel-9-series/pixel-9/`
* **Network Strategy:** Use `requests.Session()` with Headers derived strictly from the user's provided HAR/cURL trace.

## 3. DOM Structure (Verified via Screenshot)
The site uses the **Flatsome Theme**. The scraper must iterate through the grid items.

| Component | Exact CSS Selector | Logic |
| :--- | :--- | :--- |
| **Item Container** | `.product-small` | This is the card wrapper for each phone. |
| **Product Title** | `.title-wrapper .woocommerce-loop-product__title` | Extract text (e.g., "Google Pixel 9 Quốc Tế (New)"). |
| **Price Tag** | `.price-wrapper .woocommerce-Price-amount bdi` | Extract text (e.g., "14.490.000"). Note: Price is inside a `<bdi>` tag. |

## 4. Business Logic

### 4.1. Filtering & Cleaning
1.  **Loop:** Iterate through all `.product-small` elements found on the page.
2.  **Clean Price:** Remove `.` (dots) and symbols. Convert to Integer.
3.  **Filter:**
    * **MUST** contain "Pixel 9" in the title.
    * **MUST NOT** contain "Pro" (unless user wants Pro).
    * **MUST NOT** contain "Lock" (User specified banking/no-ads needs).

### 4.2. Alert Trigger
* **Target Price:** < 10,900,000 VND.
* **Action:** Send Telegram message if a valid International/Likewnew Pixel 9 is found below this price.
* **State:** Update `price_history.json` to track the lowest price seen per variant.

## 5. Output for Codex
* **Step 1:** Ask user for HAR/Header content.
* **Step 2:** Generate `main.py` using the selectors above.