import time
import discord
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, r, rate_limits):
        self.r = r
        self.rate_limits = rate_limits
        self.free_tier_limit = 5  # Set the free tier limit here

    async def check_rate_limit(self, user_id, tier=None):
        key = f"users:{user_id}"
        user_data = await self.r.hgetall(key)

        if user_data:
            reset_time = user_data.get("rate_limit_reset_time")
            if reset_time is None or time.time() >= float(reset_time):
                daily_limit = self.rate_limits.get(tier, self.free_tier_limit)
                if daily_limit == 0:
                    daily_limit = float('inf')
                await self.r.hset(key, {"rate_limit_reset_time" : str(time.time() + 86400)})
                await self.r.hset(key, {"rate_limit_count": "0"})
            else:
                count = int(user_data.get("rate_limit_count", "0"))
                daily_limit = self.rate_limits.get(tier, self.free_tier_limit)
                if count >= daily_limit:
                    reset_time_dt = datetime.fromtimestamp(float(reset_time))
                    time_remaining = reset_time_dt - datetime.now()
                    return False, time_remaining

            await self.r.hincrby(key, "rate_limit_count", 1)
            return True, None

        else:
            # Handle the case where the user hash doesn't exist
            return True, None

    async def send_rate_limit_message(self, channel, time_remaining):
        days, seconds = time_remaining.days, time_remaining.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        time_string = ""
        if days > 0:
            time_string += f"{days} day{'s' if days > 1 else ''} "
        if hours > 0:
            time_string += f"{hours} hour{'s' if hours > 1 else ''} "
        if minutes > 0:
            time_string += f"{minutes} minute{'s' if minutes > 1 else ''} "
        if seconds > 0:
            time_string += f"{seconds} second{'s' if seconds > 1 else ''}"

        embed = discord.Embed(
            title="Rate Limit Exceeded",
            description=f"You have reached the daily message limit for your subscription tier. Please try again in {time_string.strip()}.",
            color=0xFF0000
        )
        await channel.send(embed=embed)