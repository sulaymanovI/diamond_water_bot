import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database.database import init_db
from handlers import clients, sellers, orders, consumptions
from utilities.scheduler import setup_scheduler  # Changed from on_startup
from middleware.access import AccessMiddleware

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
    dp.include_router(clients.router)
    dp.include_router(sellers.router)
    dp.include_router(orders.router)
    dp.include_router(consumptions.router)
    # Регистрация middleware
    dp.update.middleware(AccessMiddleware())
    
    # Запуск бота и планировщика
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен")
    
    # Start the scheduler as a background task
    asyncio.create_task(setup_scheduler(bot))
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")