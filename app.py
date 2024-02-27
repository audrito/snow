import os
import discord
import asyncio
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationTokenBufferMemory
from langchain.memory import RedisChatMessageHistory
from langchain.chains import LLMChain
from cleanput import fix_short_forms


# Langchain Settings


llm = LlamaCpp(model_path=model_path, verbose=False, n_ctx=2048, n_batch=512, max_tokens=-1, temperature=0.8, repeat_penalty=1.18)

# Discord Settings
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_queue = asyncio.Queue()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        asyncio.create_task(self.process_requests())

    async def on_message(self, message):
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
                system_message = "You are a good AI assistant"

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
                    response = await conversation.arun({"question": fix_short_forms(message.content)})
                channel = message.channel
                await channel.send(response)

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_BOT_TOKEN)
