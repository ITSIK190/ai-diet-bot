import asyncio
import logging
from datetime import datetime
import pytz
from ai_manager import generate_response
from local_db import get_users_with_schedules, get_schedules

log = logging.getLogger(__name__)


async def send_scheduled_messages(bot):
    tz = pytz.timezone("Asia/Jerusalem")
    while True:
        now = datetime.now(tz).strftime("%H:%M")
        try:
            users = await get_users_with_schedules()
            for user in users:
                uid = user["user_id"]
                name = user.get("name", "Friend")
                for s in await get_schedules(uid):
                    if s.get("time", "").strip() == now:
                        try:
                            resp = await generate_response(uid, s.get("comment", "Time for your daily check-in!"))
                            await bot.send_message(uid, f"⏰ *{s['time']}*\n\n{resp}", parse_mode="Markdown")
                        except Exception as e:
                            log.error(f"Schedule error for {uid}: {e}")
        except Exception as e:
            log.error(f"Scheduler error: {e}")
        await asyncio.sleep(60)
