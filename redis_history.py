import json
from typing import List, Dict
import coredis
from llama_cpp import Llama
from database.read import *

class RedisHistory:
    def __init__(self, llm: Llama, max_token_limit: int, session_id: str, redis: coredis.Redis):
        self.llm = llm
        self.max_token_limit = max_token_limit
        self.session_id = session_id
        self.redis = redis
        self.key_prefix = "history:"

    @classmethod
    async def create(cls, llm: Llama, max_token_limit: int, session_id: str, redis: coredis.Redis):
        # redis = await coredis.Redis(host=redis_host, password=redis_password, port=redis_port, db=redis_db)
        return cls(llm, max_token_limit, session_id, redis)

    @property
    def key(self) -> str:
        """Construct the record key to use"""
        return self.key_prefix + self.session_id

    async def add_message(self, role: str, content: str):
        message = {'role': role, 'content': content}
        message_str = json.dumps(message)
        await self.redis.rpush(self.key, [message_str])
        await self.redis.expire(self.key, EXPIRE)

    async def get_history(self) -> List[Dict[str, str]]:
        history = await cache(self.redis.lrange(self.key, 0, -1))
        if history:
            return [json.loads(message) for message in history]
        else:
            return []

    async def truncate_history(self, history: List[Dict[str, str]], prompt, system_message=None, gap=100) -> List[Dict[str, str]]:
        total_tokens = gap
        if system_message:
            system_message_str = json.dumps(system_message)
            total_tokens += len(self.llm.tokenize(system_message_str.encode('utf-8')))
        
        prompt_str = json.dumps(prompt)
        total_tokens += len(self.llm.tokenize(prompt_str.encode('utf-8')))

        for message in history:
            message_str = json.dumps(message)
            total_tokens += len(self.llm.tokenize(message_str.encode('utf-8')))

        while total_tokens > self.max_token_limit:
            oldest_message = history.pop(0)
            oldest_message_str = json.dumps(oldest_message)
            total_tokens -= len(self.llm.tokenize(oldest_message_str.encode('utf-8')))
        keep_elements = len(history)
        total_elements = await self.redis.llen(self.key)
        remove_elements = total_elements - keep_elements
        if remove_elements > 0:
            await self.redis.ltrim(self.key, remove_elements, -1)
        return history

    async def clear_history(self):
        await self.redis.delete(self.key)
