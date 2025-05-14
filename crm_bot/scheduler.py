from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from config import Config
from notifications.order_notifications import check_one_day_orders

async def setup_scheduler(bot: Bot):
    """Настройка планировщика задач"""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    
    # Ежедневная проверка в 10:00 утра
    scheduler.add_job(
        # check_one_day_orders,
        # 'cron',
        # hour=10,
        # minute=1,
				check_one_day_orders,
				'interval',
				minutes=1,
        args=[bot, Config.TELEGRAM_CHANNEL_ID]
    )
		
    scheduler.start()