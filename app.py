from dotenv import load_dotenv
import sys
import os
import json
import re
import coredis
import discord
from discord.ext import commands
import asyncio
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.memory import RedisChatMessageHistory
from ConversationTokenBufferMemory import ConversationTokenBufferMemory
from langchain.chains import LLMChain
from cleanput import fix_short_forms
import random_replies
import autotext
from importer import import_character_from_link, client

DISCORD_BOT_TOKEN = sys.argv[1]

redis_password = sys.argv[2]

model_path = sys.argv[3]

redis_host = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com'

redis_port = 13761

redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}'

r = coredis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True, password=redis_password)

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.messages = True
intents.message_content = True

# Langchain Settings
llm = LlamaCpp(model_path=model_path, n_gpu_layers=120, verbose=False, n_ctx=8136, n_batch=1024, max_tokens=-1, temperature=1.5, repeat_penalty=1.3, top_k=20)

def is_valid_message(message):
    if message.attachments or message.stickers:
        return False
    if not message.content.strip():
        return False
    return True

# Discord Settings
class MyClient(commands.Bot, discord.Client):
    def __init__(self, intents: discord.Intents, *args, **kwargs):
        super().__init__(command_prefix="!", intents=intents, case_insensitive=True, *args, **kwargs)
        self.request_queue = asyncio.Queue()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        asyncio.create_task(self.process_requests())
        asyncio.create_task(autotext.check_for_follow_ups(self, r))
        await self.tree.sync()
        print("Tree synced")


    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if self.user != message.author:
            user_id = str(message.author.id)
            if not await r.exists([f'user:{user_id}']):
                await r.hset(f'user:{user_id}', {'selected_character': 895743})
                print(f'New user profile created for {message.author.id}!')
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
                character_id = await r.hget(f'user:{user_id}', 'selected_character')
                session_id = ':'.join([user_id, 'character', character_id])
                history = RedisChatMessageHistory(session_id=session_id, url=redis_url)
                memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=2048, chat_memory=history)
                character_data = await r.json.get(f'character:{character_id}')
                cleaned_character_data = re.sub(r'\{\{(.*?)\}\}', r'{\1}', character_data['data']['description'])
                if character_data['data']['first_mes']:
                    cleaned_character_first_mes = re.sub(r'\{\{(.*?)\}\}', r'{\1}', character_data['data']['first_mes'])
                    cleaned_character_first_mes = ":".join (['AI', cleaned_character_first_mes])
                else:
                    cleaned_character_first_mes = ""
                system_message = f"Continue the conversation by generating a single message while roleplaying the following character.{cleaned_character_data}\n{cleaned_character_first_mes}\nPrevious Conversation: {cleaned_character_first_mes}"
                template = "{history}\n{user}:{question}\n{char}:"

                new_template = "\n".join([system_message, template])
                prompt = PromptTemplate(template=new_template, input_variables=["question"], partial_variables={"user": "you", "char": "Katy"})
                conversation = LLMChain(
                    llm=llm,
                    prompt=prompt,
                    verbose=False,
                    memory=memory
                )
                # Show typing... indicator
                async with message.channel.typing():
                    cleaned_message = fix_short_forms(message.content)
                    if not cleaned_message.strip():
                        response = random_replies.blank_message_reply()
                        history.add_user_message(cleaned_message)
                        history.add_ai_message(response)
                    else:
                        response = await conversation.arun({'question':cleaned_message})
                channel = message.channel
                await channel.send(response)

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
                    await r.hset(f'user:{user_id}', {'selected_character': code})

        character_id = await r.hget(f'user:{user_id}', 'selected_character')
        character_data = await r.json.get(f'character:{character_id}')
        if character_data['data']['first_mes']:
            await autotext.send_first_text(self, payload.user_id, code, character_data['data']['first_mes'])


client = MyClient(intents=intents)


@client.hybrid_command(name="import_character", description="Import a character from the Chub API")
async def import_character(ctx: commands.Context, link:str):
    # if not any(link.startswith(prefix) for prefix in ["https://chub.ai", "http://chub.ai", "http://www.chub.ai" "https://www.chub.ai", "www.chub.ai", "chub.ai"]):
    #     await ctx.send(f"Currently, we support importing characters from www.chub.ai only.")
    # else:
    await ctx.defer()
    await import_character_from_link(link, client=client, r=r)
    await ctx.send("Character imported!")

client.run(DISCORD_BOT_TOKEN)
