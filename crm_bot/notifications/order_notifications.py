from aiogram import Bot
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from database.models import Order, Client, Seller
from database.utils import async_session

async def send_order_notification_to_channel(bot: Bot, order: Order, channel_id: str):
    """Отправка уведомления о заказе в канал"""
    message_text = (
        "🔔 *1-дневное уведомление о заказе*\n\n"
        f"🆔 *Номер заказа*: `#{order.id}`\n"
        f"📅 *Дата создания*: `{order.created_at.strftime('%d.%m.%Y %H:%M')}`\n"
        f"👤 *Клиент*: {order.client.full_name}\n"
        f"📞 *Телефон*: `{order.client.phone}`\n"
        f"🛒 *Количество товара*: `{order.item_count} шт.`\n"
        f"💵 *Предоплата*: `{order.prepaid or 0} сум`\n"
        f"👨‍💼 *Продавец*: {order.seller.full_name}"
    )
    
    await bot.send_message(
        chat_id=channel_id,
        text=message_text,
        parse_mode="Markdown"
    )
    
async def check_one_day_orders(bot: Bot, channel_id: str):
    """Проверка заказов (ТЕСТОВАЯ ВЕРСИЯ)"""
    async with async_session() as session:
        # Изменяем на 1 минуту вместо 1 дня для теста
        test_time = datetime.now() - timedelta(minutes=1)
        
        query = (
            select(Order)
            .where(Order.created_at.between(
                test_time - timedelta(minutes=1),
                test_time + timedelta(minutes=1)
            ))
            .join(Client)
            .join(Seller)
        )
        
        # Добавляем логирование
        print(f"Ищем заказы между: {test_time - timedelta(minutes=1)} и {test_time + timedelta(minutes=1)}")
        
        result = await session.execute(query)
        orders = result.scalars().all()
        
        print(f"Найдено заказов: {len(orders)}")
        
        for order in orders:
            print(f"Отправляем уведомление для заказа #{order.id}")
            await send_order_notification_to_channel(bot, order, channel_id)
        
        return len(orders)

# async def check_one_day_orders(bot: Bot, channel_id: str):
#     """Проверка заказов, которым исполнился 1 день"""
#     async with async_session() as session:
#         one_day_ago = datetime.now() - timedelta(days=1)
        
#         query = (
#             select(Order)
#             .where(Order.created_at.between(
#                 one_day_ago - timedelta(minutes=5),
#                 one_day_ago + timedelta(minutes=5)
#             ))
#             .join(Client)
#             .join(Seller)
#         )
        
#         result = await session.execute(query)
#         orders = result.scalars().all()
        
#         for order in orders:
#             await send_order_notification_to_channel(bot, order, channel_id)
        
#         return len(orders)