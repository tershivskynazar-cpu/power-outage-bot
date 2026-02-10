import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    POWERON_URL = "https://poweron.loe.lviv.ua/"
    LOE_API_BASE_URL = "https://api.loe.lviv.ua"
    LOE_API_PREFIX = "/api"
    LOE_API_SCHEDULE_MENU_TYPE = "photo-grafic"
    LOE_API_GROUPS_MENU_TYPE = "power-group"
    
    CHECK_INTERVAL_MINUTES = 10
    
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    DATA_FILE = "user_data.json"
    
    # Використовувати тестові дані для розробки
    USE_TEST_DATA = os.getenv('USE_TEST_DATA', 'false').lower() == 'true'
    
    # Групи тепер визначаються динамічно парсером
    FALLBACK_GROUPS = [
        "1.1", "1.2",
        "2.1", "2.2",
        "3.1", "3.2",
        "4.1", "4.2",
        "5.1", "5.2",
        "6.1", "6.2",
    ]
    
    @classmethod
    def validate_token(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            print("⚠️ TELEGRAM_BOT_TOKEN не знайдено! Бот не працюватиме без токена.")
            return False
        return True
