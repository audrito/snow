import discord
import asyncio
from datetime import datetime, timedelta

async def send_first_text(client, user_id, character_id, first_mes):
    user = await client.fetch_user(user_id)
    await user.send(first_mes)

async def send_follow_up_text(client, user_id, character_id, follow_up_mes):
    user = await client.fetch_user(user_id)
    await user.send(follow_up_mes)

async def check_for_follow_ups(client, r):
    while True:
        async for user_id in r.scan_iter(f"user:*"):
            last_interaction = await r.hget(user_id, "last_interaction")
            if last_interaction:
                last_interaction = datetime.fromisoformat(last_interaction)
                character_id = await r.hget(user_id, "selected_character")
                character_data = await r.json.get(f"character:{character_id}")

                # Send one-day follow-up
                if datetime.now() - last_interaction >= timedelta(days=1):
                    await send_follow_up_text(client, int(user_id.split(":")[1]), character_id, character_data["data"]["follow_up_1"])

                # Send three-day follow-up
                if datetime.now() - last_interaction >= timedelta(days=3):
                    await send_follow_up_text(client, int(user_id.split(":")[1]), character_id, character_data["data"]["follow_up_3"])

        await asyncio.sleep(3600)  # Check every hour