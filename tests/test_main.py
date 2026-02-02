import json
from types import SimpleNamespace

import main


def _mock_response(html: str, status: int = 200):
    return SimpleNamespace(status_code=status, content=html.encode('utf-8'))


def test_clean_price():
    assert main.clean_price(None) == 0
    assert main.clean_price("") == 0
    assert main.clean_price("14.490.000 ?") == 14490000
    assert main.clean_price("2,345,000") == 2345000
    assert main.clean_price("abc") == 0


def test_main_filters_and_logs(monkeypatch, tmp_path):
    html = """
    <html><body>
        <div class="product-small">
            <h3 class="woocommerce-loop-product__title">Google Pixel 9 Qu?c T? (New)</h3>
            <span class="price"><span class="woocommerce-Price-amount"><bdi>14.490.000 ?</bdi></span></span>
        </div>
        <div class="product-small">
            <h3 class="woocommerce-loop-product__title">Google Pixel 9 Pro</h3>
            <span class="price"><span class="woocommerce-Price-amount"><bdi>20.000.000 ?</bdi></span></span>
        </div>
        <div class="product-small">
            <h3 class="woocommerce-loop-product__title">Google Pixel 9 Lock</h3>
            <span class="price"><span class="woocommerce-Price-amount"><bdi>9.000.000 ?</bdi></span></span>
        </div>
        <div class="product-small">
            <h3 class="woocommerce-loop-product__title">Google Pixel 9 Qu?c T? (New)</h3>
            <span class="price"><span class="woocommerce-Price-amount"><bdi>14.490.000 ?</bdi></span></span>
        </div>
        <div class="product-small">
            <h3 class="woocommerce-loop-product__title">Google Pixel 9 Qu?c T?</h3>
            <span class="price"><span class="woocommerce-Price-amount"><bdi>1.000.000 ?</bdi></span></span>
        </div>
    </body></html>
    """

    # Isolate filesystem outputs
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "HISTORY_FILE", str(tmp_path / "history.json"))
    monkeypatch.setattr(main, "LOG_FILE", str(tmp_path / "log.csv"))
    monkeypatch.setattr(main, "IMG_FILE", str(tmp_path / "chart.png"))

    # Mock network + side effects
    monkeypatch.setattr(main.cffi, "get", lambda *args, **kwargs: _mock_response(html))
    monkeypatch.setattr(main, "draw_chart", lambda: False)

    sent_messages = []
    monkeypatch.setattr(main, "send_telegram_text", lambda msg: sent_messages.append(msg))
    monkeypatch.setattr(main, "send_telegram_photo", lambda caption: sent_messages.append(caption))
    monkeypatch.setattr(main, "send_telegram_alert", lambda msg: sent_messages.append(msg))

    logged = []
    monkeypatch.setattr(main, "log_to_csv", lambda title, price: logged.append((title, price)))

    main.main()

    # Only the valid, non-duplicate, non-pro, non-lock, realistic price product is logged
    assert logged == [("Google Pixel 9 Qu?c T? (New)", 14490000)]

    with open(main.HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
    assert history == {"Google Pixel 9 Qu?c T? (New)": 14490000}

    assert sent_messages, "Expected a summary message to be sent"
    assert "Google Pixel 9 Qu?c T? (New)" in sent_messages[0]


def test_main_selector_fallback(monkeypatch, tmp_path):
    # No .product-small, but .type-product exists -> should still parse
    html = """
    <html><body>
        <div class="type-product">
            <h3 class="product-title">Google Pixel 9 Qu?c T?</h3>
            <span class="amount">12.000.000 ?</span>
        </div>
    </body></html>
    """

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "HISTORY_FILE", str(tmp_path / "history.json"))
    monkeypatch.setattr(main, "LOG_FILE", str(tmp_path / "log.csv"))
    monkeypatch.setattr(main, "IMG_FILE", str(tmp_path / "chart.png"))

    monkeypatch.setattr(main.cffi, "get", lambda *args, **kwargs: _mock_response(html))
    monkeypatch.setattr(main, "draw_chart", lambda: False)
    monkeypatch.setattr(main, "send_telegram_text", lambda msg: None)
    monkeypatch.setattr(main, "send_telegram_photo", lambda caption: None)
    monkeypatch.setattr(main, "send_telegram_alert", lambda msg: None)

    logged = []
    monkeypatch.setattr(main, "log_to_csv", lambda title, price: logged.append((title, price)))

    main.main()

    assert logged == [("Google Pixel 9 Qu?c T?", 12000000)]


def test_main_no_products_triggers_alert(monkeypatch, tmp_path):
    html = "<html><body><div class=\"nope\"></div></body></html>"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "HISTORY_FILE", str(tmp_path / "history.json"))
    monkeypatch.setattr(main, "LOG_FILE", str(tmp_path / "log.csv"))
    monkeypatch.setattr(main, "IMG_FILE", str(tmp_path / "chart.png"))

    monkeypatch.setattr(main.cffi, "get", lambda *args, **kwargs: _mock_response(html))

    alerts = []
    monkeypatch.setattr(main, "send_telegram_alert", lambda msg: alerts.append(msg))
    monkeypatch.setattr(main, "send_telegram_text", lambda msg: None)
    monkeypatch.setattr(main, "send_telegram_photo", lambda caption: None)

    main.main()

    assert alerts, "Expected alert when no products are found"
    assert (tmp_path / "error_page.html").exists()
