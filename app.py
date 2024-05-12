from dotenv import load_dotenv
import os
import json
import re
import string
import coredis
import textwrap
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import describe
from discord import File
import asyncio
from llama_cpp import Llama
from redis_history import RedisHistory
from cleanput import fix_short_forms
import random_replies
from importer import import_character_from_link, save_custom_character, client
from database.read import cache
from database.database import *
from database.write import scan_expiring_keys, permanent_delete
from user import *

from rate_limiter import RateLimiter

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

MODEL_PATH = os.getenv('MODEL_PATH')

# redis_password = os.environ.get("REDIS_PASSWORD")
# redis_host = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com'
# redis_port = 13761
# redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"

# r = coredis.Redis(host=redis_host, port=redis_port, password=redis_password, db=0, decode_responses=True)

llm = Llama(model_path=MODEL_PATH, chat_format='alpaca', n_gpu_layers=20, verbose=True, n_ctx=4096, n_batch=1024, max_tokens=-1, temperature=1.5, repeat_penalty=1.3, top_k=20)


intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.messages = True
intents.message_content = True

# Paywall Settings

rate_limits = {
    "Snowflake": 70,
    "Snowfall": 200,
    "Snowstorm": float('inf')
}
rate_limiter = RateLimiter(r, rate_limits)

# Discord Settings
class MyClient(commands.Bot, discord.Client):
    def __init__(self, intents: discord.Intents, *args, **kwargs):
        super().__init__(command_prefix="!", intents=intents, case_insensitive=True, *args, **kwargs)
        self.request_queue = asyncio.Queue()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        asyncio.create_task(self.process_requests())
        asyncio.create_task(scan_expiring_keys())
        await self.tree.sync()
        print("Tree synced")


    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if self.user != message.author:
            user_id = str(message.author.id)
            await create_user(user_id)
            await self.request_queue.put(message)
                
    async def process_requests(self):
        while True:
            # Get one message from the queue
            message = await self.request_queue.get()
            # Process the message
            await self.process_request(message)

    async def process_request(self, message):
        if self.user != message.author:
            if message.channel.type == discord.ChannelType.private or self.user in message.mentions:
                user_id = str(message.author.id)
                tier = await cache(r.hget(f'users:{user_id}', 'Tier'))
                if tier is None or tier.lower() == 'free':
                    tier = None
                allowed, time_remaining = await rate_limiter.check_rate_limit(user_id, tier)
                if not allowed:
                    await rate_limiter.send_rate_limit_message(message.channel, time_remaining)
                    return
                character_id = await cache(r.hget(f'users:{user_id}', 'selected_character'))
                session_id = ':'.join([user_id, 'character', character_id])
                history = await RedisHistory.create(llm, session_id=session_id, max_token_limit=4096, redis=r)
                character_data = await cache(r.json.get(f'characters:{character_id}'))
                cleaned_character_data = re.sub('{{user}}', 'you', re.sub('{{char}}', character_data['data']['name'], character_data['data']['description']))
                system_message = {'role': 'system', 'content': f"Continue while roleplaying the following character.{cleaned_character_data}"}
                # Show typing... indicator
                async with message.channel.typing():
                    cleaned_message = fix_short_forms(message.content)
                    validated_message = random_replies.validate(cleaned_message)

                    if validated_message != True:
                        assistant_reply = validated_message
                    else:
                        messages = await history.get_history()
                        if not messages:
                            messages.append(system_message)
                            messages.append({'role': 'user', 'content': cleaned_message})
                        else:
                            messages = await history.truncate_history(history=messages, prompt={'role': 'user', 'content': cleaned_message}, system_message=system_message)
                            messages.insert(0, system_message)
                            messages.append({'role': 'user', 'content': cleaned_message})
                        gap = 100
                        while True:
                            try:
                                response = await asyncio.get_event_loop().run_in_executor(None, llm.create_chat_completion, messages)
                                break
                            except ValueError:
                                gap += 100
                                messages = await history.truncate_history(history=messages, prompt={'role': 'user', 'content': cleaned_message}, gap=gap)

                        assistant_reply = response['choices'][0]['message']['content']

                        while not assistant_reply.strip():
                            response = await asyncio.get_event_loop().run_in_executor(None, llm.create_chat_completion, messages)
                            assistant_reply = response['choices'][0]['message']['content']

                        await history.add_message('user', cleaned_message)
                        await history.add_message('assistant', assistant_reply)

                chunks = textwrap.wrap(assistant_reply, width=2000, break_long_words=False)
                for chunk in chunks:
                    await message.channel.send(chunk)
                # await channel.send(assistant_reply)

    async def on_raw_reaction_add(self, payload):
        user_id = str(payload.user_id)
        channel = client.get_channel(payload.channel_id)
        if channel is not None:
            if isinstance(channel, discord.Thread) and channel.parent_id == 1143741288655622178:
                # Get the message content
                message = await channel.fetch_message(payload.message_id)
                message_content = message.content
                # Extract the last 4 characters from the message content
                match = re.search(r'\[(\d{6})\]$', message_content)
                if match:
                    code = match.group(1)

                    # Update the hash for the user with the extracted 4 character code
                    await r.hset(f'users:{user_id}', {'selected_character': code})
                    await r.expire(f'users:{user_id}', EXPIRE)

        character_id = await cache(r.hget(f'users:{user_id}', 'selected_character'))
        character_data = await cache(r.json.get(f'characters:{character_id}'))

    async def on_member_update(self, before, after):
        # Check if the update happened in the specific server
        if before.guild.id != 1143737958701203526:
            return
        if not await r.exists([f'users:{after.id}']):
            await create_user(after.id)
        # List of roles to check in order of priority (highest to lowest)
        roles_to_check = ["Snowstorm", "Snowfall", "Snowflake"]
        # Find the highest role that was added or remains present
        highest_role_name = None
        for role_name in roles_to_check:
            role = discord.utils.get(after.guild.roles, name=role_name)
            if role in after.roles:
                highest_role_name = role_name
                break
        # If no role was found, set the "Tier" field to "Free"
        if highest_role_name is None:
            await r.hset(f'users:{after.id}', {'Tier': 'Free'})
            print(f"Updated 'Tier' field to 'Free' for user {after.display_name}")
            return
        # Check if the user had any of the roles before
        had_role = False
        for role_name in roles_to_check:
            role = discord.utils.get(before.guild.roles, name=role_name)
            if role in before.roles:
                had_role = True
                break
        # If the user had a role and the highest role is the same as before, do nothing
        if had_role and highest_role_name == before.top_role.name:
            return
        # Update the "Tier" field in Redis with the highest role name
        await r.hset(f'users:{after.id}', {'Tier': highest_role_name})
        print(f"Updated 'Tier' field to '{highest_role_name}' for user {after.display_name}")

client = MyClient(intents=intents)

@client.hybrid_command(name="import_character", description="Import a character from the Chub API")
async def import_character(ctx: commands.Context, link:str):
    if not any(link.startswith(prefix) for prefix in ["https://chub.ai", "http://chub.ai", "http://www.chub.ai" "https://www.chub.ai", "www.chub.ai", "chub.ai"]):
        await ctx.send(f"Currently, we only support importing characters from www.chub.ai.")
    else:
        await ctx.defer()
        import_status = await import_character_from_link(link, client=client, r=r)
        if import_status:
            url = await r.json.get(f'characters:{import_status}','postlink')
            await ctx.send(f"Character Successfully Imported. Go to this post and react to select the character.\n{url}")
        else:
            await ctx.send("The character was recently updated in chub and unable to import until next 24 hours, please choose another character.")


@client.tree.command(name="create_character", description="Create a custom character")
@app_commands.rename(image="character_image")
async def create_character(
    interaction: discord.Interaction,
    name: str,
    age: app_commands.Range[int, 18, None],
    description: str,
    image: discord.Attachment = None):
    userID = interaction.user.id

    char_data = {
        "data": {
            "creator": userID,
            "name": name,
            "age": age,
            "description": description
        }
    }

    image_path = None
    if image:
        directory = "custom_character_images"
        os.makedirs(directory, exist_ok=True)
        _, file_extension = os.path.splitext(image.filename)
        image_path = os.path.join(directory, f"{name}{file_extension}")
        # Save the image data directly
        with open(image_path, 'wb') as f:
            await image.save(f)

    message_url = await save_custom_character(r=r, char_data=char_data, image_path=image_path, userID=userID, client=client)
    await interaction.response.send_message(f"Your character has been created\n{message_url}")

@client.tree.command(name="random_character", description="Select a random character")
async def random_character(interaction: discord.Interaction):
    user_id = interaction.user.id
    # Assuming 'character_id_list' is the key of your set in Redis
    redis_set = await r.smembers('character_id_list')

    # Check if the set is empty
    if not redis_set:
        await interaction.response.send_message("There is no character to choose from.")
        return

    # Select a random item from the set
    random_code = random.choice(tuple(redis_set))
    await r.hset(f'users:{user_id}', {'selected_character': random_code})
    data = await r.json.get(f'characters:{random_code}')
    
    await interaction.response.send_message(f"The randomly selected character ID is: {data['postlink']}")

@client.tree.command(name="clear_history", description="Clear your conversation history from memory.")
async def clear_history(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    character_id = await r.hget(f'users:{user_id}', 'selected_character')
    session_id = ':'.join([user_id, 'character', character_id])

    # Delete the message store key for the current user and character
    await permanent_delete(r.delete(f'history:{session_id}'))

    await interaction.response.send_message(f"Your conversation history has been cleared.", ephemeral=True)

client.run(DISCORD_BOT_TOKEN)
