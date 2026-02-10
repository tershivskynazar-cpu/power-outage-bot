from bot import PowerOutageBot

def main():
    bot = PowerOutageBot()
    bot.application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
