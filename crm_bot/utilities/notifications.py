import logging
from datetime import datetime, timedelta
from typing import List
import asyncio
from aiogram import Bot
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload
from database.utils import async_session
from database.models import Order, Client
from config import Config

async def get_orders_reaching_one_month(session):  # Added session parameter
    """
    Fetch orders that have reached 1 month since creation
    and haven't been notified yet or need reminder
    """
    one_month_ago = datetime.now() - timedelta(days=30)  # Changed from seconds to days
        
    result = await session.execute(
        select(Order)
        .where(
            Order.created_at <= one_month_ago,
            or_(
                Order.last_notification_sent == None,
                Order.last_notification_sent < one_month_ago
            )
        )
        .options(joinedload(Order.client)))
    return result.scalars().all()

async def send_order_notification(bot: Bot, order: Order) -> bool:
    """
    Send notification about a specific order to the channel
    Returns True if successful, False otherwise
    """
    try:
        message = (
            "⚠️ 1 oy bo'ldi! Buyurtma haqida eslatma:\n\n"
            f"📋 Buyurtma ID: #{order.id}\n"
            f"👤 Mijoz: {order.client.full_name}\n"
            f"📞 Tel: {order.client.phone}\n"
            f"💰 Umumiy summa: {order.sum_of_item:,} so'm\n"
            f"💳 To'langan: {order.total_paid:,} so'm\n"
            f"🔄 Qoldiq: {order.remaining_amount:,} so'm\n"
            f"📅 Buyurtma sanasi: {order.created_at.strftime('%Y-%m-%d')}\n\n"
            f"@diamond_water_crm_bot"
        )
        
        await bot.send_message(
            chat_id=Config.TELEGRAM_CHANNEL_ID,
            text=message
        )
        return True
    except Exception as e:
        logging.error(f"Failed to send notification for order {order.id}: {str(e)}")
        return False

async def update_notification_status(session, order_id: int) -> None:
    """
    Update the notification tracking fields in database
    """
    try:
        order = await session.get(Order, order_id)
        if order:
            order.last_notification_sent = datetime.now()
            order.notification_count += 1
            await session.commit()
    except Exception as e:
        logging.error(f"Failed to update notification status for order {order_id}: {str(e)}")
        await session.rollback()
        raise

async def check_and_notify_orders(bot: Bot) -> None:
    """
    Main function to check for due orders and send notifications
    """
    async with async_session() as session:
        try:
            orders = await get_orders_reaching_one_month(session)  # Now passing session
            if not orders:
                logging.info("No orders requiring notification found")
                return

            logging.info(f"Found {len(orders)} orders requiring notification")
            
            for order in orders:
                success = await send_order_notification(bot, order)
                if success:
                    await update_notification_status(session, order.id)
                    logging.info(f"Notification sent for order #{order.id}")
                else:
                    logging.warning(f"Failed to send notification for order #{order.id}")
                await asyncio.sleep(1)  # Rate limitin  g

        except Exception as e:
            logging.error(f"Error in notification system: {str(e)}")
            await session.rollback()
        finally:
            await session.close()

async def get_monthly_order_statistics(session):
    """
    Calculate monthly statistics for all orders
    Returns: dict with sums of item_count, total_paid, remaining_amount, sum_of_item
    """
    result = await session.execute(
        select(
            func.sum(Order.item_count).label("total_items"),
            func.sum(Order.total_paid).label("total_paid"),
            func.sum(Order.remaining_amount).label("total_remaining"),
            func.sum(Order.sum_of_item).label("total_sum")
        )
    )
    return result.one()

async def send_monthly_report(bot: Bot) -> bool:
    """
    Send monthly statistics report to the channel
    Returns True if successful, False otherwise
    """
    async with async_session() as session:
        try:
            stats = await get_monthly_order_statistics(session)
            total_items, total_paid, total_remaining, total_sum = stats
            
            uzbek_months = [
                "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
                "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"
            ]

            # Get the first day of the current month
            first_day_of_this_month = datetime.now().replace(day=1)

            # Subtract one day to get a date from the previous month
            last_month_date = first_day_of_this_month - timedelta(days=1)

            # Use Uzbek month name
            month_name = uzbek_months[last_month_date.month - 1]
            year = last_month_date.year
            
            current_month = f"{month_name} {year}"

            message = (
                f"📊 {current_month} uchun hisobot:\n\n"
                f"📦 Jami buyurtmalar soni: {total_items or 0}\n"
                f"💰 Jami summa: {total_sum or 0:,} so'm\n"
                f"💳 Jami to'langan: {total_paid or 0:,} so'm\n"
                f"🔄 Jami qoldiq: {total_remaining or 0:,} so'm\n\n"
                f"@diamond_water_crm_bot"
            )
            
            await bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=message
            )
            return True
        except Exception as e:
            logging.error(f"Failed to send monthly report: {str(e)}")
            return False