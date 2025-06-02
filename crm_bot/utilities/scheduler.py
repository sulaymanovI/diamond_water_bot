import aioschedule
import asyncio
from aiogram import Bot
from utilities.notifications import check_and_notify_orders, send_monthly_report
import logging
from datetime import datetime, timedelta

async def setup_scheduler(bot: Bot):
    while True:
        now = datetime.now()
        
        # Production - run at 10:00 AM daily
        if now.hour == 10 and now.minute == 0:
            await check_and_notify_orders(bot)
            
            # Monthly report on 1st day of month
            if now.day == 1:
                await send_monthly_report(bot)
            
            await asyncio.sleep(60)  # Prevent multiple runs
        
        ##Testing - run every 5 minutes
        elif now.minute % 2 == 0:
            await check_and_notify_orders(bot)
            await send_monthly_report(bot)

            await asyncio.sleep(60)
                
        else:
            await asyncio.sleep(10)  # Check every 10 seconds