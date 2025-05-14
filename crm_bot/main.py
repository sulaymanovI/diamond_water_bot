import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database.database import init_db
from handlers import common, clients, sellers, orders
from notifications.order_notifications import check_one_day_orders
from scheduler import setup_scheduler
from middleware.access import AccessMiddleware

async def on_startup(bot: Bot):
    """Функция, выполняемая при запуске бота"""
    await setup_scheduler(bot)
    
    try:
        await bot.send_message(
            chat_id=Config.TELEGRAM_CHANNEL_ID,
            text="✅ Бот и система уведомлений успешно запущены!"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение в канал: {e}")

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    
    # Инициализация БД
    await init_db()
    
    # Создание экземпляра бота
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация хэндлеров
    clients.register_handlers(dp)
    sellers.register_handlers(dp)
    orders.register_handlers(dp)
    
    # Регистрация функции запуска
    dp.startup.register(on_startup)
    dp.update.middleware(AccessMiddleware())
    
    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")