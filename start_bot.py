from config import Config
from bot import PowerOutageBot

def main():
    if not Config.validate_token():
        print("❌ Бот не може запуститися без TELEGRAM_BOT_TOKEN")
        print("📝 Додайте змінну середовища в Railway:")
        print("   TELEGRAM_BOT_TOKEN=8543970268:AAFSadbDhLCHWtN9CxOMdYcuQNpxxCdV7c4")
        return
    
    bot = PowerOutageBot()
    bot.application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
