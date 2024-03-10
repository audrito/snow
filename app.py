import os
import json
import re
import coredis
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
llm = LlamaCpp(model_path=model_path, n_gpu_layers=70, verbose=False, n_ctx=4096, n_batch=512, max_tokens=-1, temperature=1, repeat_penalty=1.2)

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
                system_message = f"Continue the conversation by generating a single message while roleplaying the following character.{cleaned_character_data}"
                template = '''Previous conversation:
{history}
{user}:{question}
{char}:'''

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
                    await r.hset(f'user:{user_id}', 'selected_character', code)

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.messages = True
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_BOT_TOKEN)
