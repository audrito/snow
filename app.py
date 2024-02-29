import os
import discord
import asyncio
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.memory import RedisChatMessageHistory
from ConversationTokenBufferMemory import ConversationTokenBufferMemory
from langchain.chains import LLMChain
from cleanput import fix_short_forms

# Langchain Settings

MODEL_PATH = "/content/snow/models/models--TheBloke--Thespis-Mistral-7B-v0.6-GGUF/snapshots/4f592294df9562c246e632dec8445d3965d84baa/thespis-mistral-7b-v0.6.Q8_0.gguf"

llm = LlamaCpp(model_path=MODEL_PATH, n_gpu_layers=120, n_ctx=4096, n_batch=1024, max_tokens=-1, temperature=0.9, repeat_penalty=1.18, verbose=False)

# Discord Settings
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_queue = asyncio.Queue()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        asyncio.create_task(self.process_requests())

    async def on_message(self, message):
        print(f'Message from {message.author.id}: {message.content}')
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
            history = RedisChatMessageHistory(session_id=session_id, url="redis://localhost:6379")
            memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=2048, chat_memory=history)

            if message.channel.type == discord.ChannelType.private or self.user in message.mentions:
                system_message = "Act as a good, supportive and romantic girlfriend."

                template = '''Previous conversation:
                {history}
                Human: {question}
                AI:'''

                new_template = "\n".join([system_message, template])

                prompt = PromptTemplate.from_template(new_template)
                conversation = LLMChain(
                    llm=llm,
                    prompt=prompt,
                    verbose=True,
                    memory=memory
                )
                # Show typing... indicator
                async with message.channel.typing():
                    response = await conversation.arun({"question": fix_short_forms(message.content)})
                channel = message.channel
                await channel.send(response)

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_BOT_TOKEN)
