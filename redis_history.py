import json
from typing import List, Dict
import coredis
from llama_cpp import Llama

class RedisHistory:
    def __init__(self, llm: Llama, max_token_limit: int, session_id: str, redis: coredis.Redis):
        self.llm = llm
        self.max_token_limit = max_token_limit
        self.session_id = session_id
        self.redis = redis
        self.key_prefix = "message_store:"

    @classmethod
    async def create(cls, redis_password, llm: Llama, max_token_limit: int, session_id: str, redis_host: str = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com', redis_port: int = 13761, redis_db: int = 0):
        redis = await coredis.Redis(host=redis_host, password=redis_password, port=redis_port, db=redis_db)
        return cls(llm, max_token_limit, session_id, redis)

    @property
    def key(self) -> str:
        """Construct the record key to use"""
        return self.key_prefix + self.session_id

    async def add_message(self, role: str, content: str):
        message = {'role': role, 'content': content}
        message_str = json.dumps(message)
        await self.redis.rpush(self.key, [message_str])

    async def get_history(self) -> List[Dict[str, str]]:
        history = await self.redis.lrange(self.key, 0, -1)
        return [json.loads(message.decode('utf-8')) for message in history]

    async def truncate_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        total_tokens = 0
        for message in history:
            message_str = json.dumps(message)
            total_tokens += len(self.llm.tokenize(message_str.encode('utf-8')))

        while total_tokens > self.max_token_limit:
            oldest_message = history.pop(0)
            oldest_message_str = json.dumps(oldest_message)
            total_tokens -= len(self.llm.tokenize(oldest_message_str.encode('utf-8')))
        return history

    async def clear_history(self):
        await self.redis.delete(self.key)