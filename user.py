from database.database import *
from database.read import cache

async def create_user(user_id, default_character_id=895743):
    key = f'users:{user_id}'
    if not await r.sismember('system:user_id_list', key):
        await r.hset(key,{'selected_character': default_character_id})
        await r.expire(key, EXPIRE)
        print(f'New user profile created for {key}!')
        await r.sadd('system:user_id_list', [key])
    else:
        await cache(r.hgetall(key))
    return