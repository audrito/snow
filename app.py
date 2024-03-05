import os
import json
import re
import redis
import discord
import asyncio
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.memory import RedisChatMessageHistory
from ConversationTokenBufferMemory import ConversationTokenBufferMemory
from langchain.chains import LLMChain
from cleanput import fix_short_forms

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

redis_password = os.environ.get("REDIS_PASSWORD")

redis_host = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com'

redis_port = 13761

redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}'

r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True, password=redis_password)

# redis_url = "redis://localhost:6379"

# r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


# Langchain Settings
llm = LlamaCpp(model_path="C:\espis-mistral-7b-v0.6.Q6_K.gguf", verbose=False, n_ctx=2048, n_batch=512, max_tokens=-1, temperature=0.9, repeat_penalty=1.18)

# Discord Settings
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_queue = asyncio.Queue()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        asyncio.create_task(self.process_requests())


    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if self.user != message.author:
            await self.request_queue.put(message)

    async def process_requests(self):
        while True:
            # Get one message from the queue
            message = await self.request_queue.get()
            # Process the message
            await self.process_request(message)

    async def process_request(self, message):
        if self.user != message.author:
            session_id = str(message.author.id)
            history = RedisChatMessageHistory(session_id=session_id, url=redis_url)
            memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=2048, chat_memory=history)

            if message.channel.type == discord.ChannelType.private or self.user in message.mentions:
                try:
                    character_id = r.hget(f'user:{session_id}', 'selected_character')
                    character_data = r.json().get(f'character:{character_id}')
                    system_message = f"Act and roleplay as the following character.\n{character_data['data']['description']}"
                except:
                    system_message = "Act and roleplay as the following character."

                template = '''Previous conversation:
{history}
Human: {question}
AI:'''

                new_template = "\n".join([system_message, template])

                prompt = PromptTemplate.from_template(new_template)
                conversation = LLMChain(
                    llm=llm,
                    prompt=prompt,
                    verbose=False,
                    memory=memory
                )
                # Show typing... indicator
                async with message.channel.typing():
                    response = await conversation.arun({"question": (message.content)})
                channel = message.channel
                await channel.send(response)

    async def on_raw_reaction_add(self, payload):
        channel = client.get_channel(payload.channel_id)
        if channel is not None:
            if isinstance(channel, discord.Thread) and channel.parent_id == 1214559209593511936:
                # Get the message content
                message = await channel.fetch_message(payload.message_id)
                message_content = message.content
                # Extract the last 4 characters from the message content
                match = re.search(r'\[(\d{6})\]$', message_content)
                if match:
                    code = match.group(1)
                    # Get the user id
                    user_id = str(payload.user_id)

                    # Update the hash for the user with the extracted 4 character code
                    r.hset(f'user:{user_id}', 'selected_character', code)

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.messages = True
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_BOT_TOKEN)
