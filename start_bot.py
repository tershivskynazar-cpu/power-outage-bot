import asyncio
from bot import PowerOutageBot

def main():
    bot = PowerOutageBot()
    
    # Start monitoring in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Start monitoring task
        loop.create_task(bot.schedule_monitor.start_monitoring(bot))
        
        # Run bot
        bot.application.run_polling(drop_pending_updates=True)
    finally:
        loop.close()

if __name__ == '__main__':
    main()
