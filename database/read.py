from database.database import *
import asyncio
import json

async def redis_any_set(key: str, value, ttl=EXPIRE):
    """Redis any set is a function to set the value of or create a key depending on it's value type with a single function call using a bunch of if/else conditionals under the hood.
    Arguments :
    key: str = The key to set.
    value = The value, can be a list, dictionary or json string for now.
    """
    if isinstance(value, dict):
        await r.hmset(key, value)
    elif isinstance(value, list):
        await r.rpush(key, value)
    elif isinstance(value, (str, bytes)):
        try:
            json_data = json.loads(value)
            await r.json.set(key,'.', json_data)
        except json.JSONDecodeError:
            await r.set(key, value)
    else:
        await r.set(key, str(value))
    await r.expire(key, ttl)

async def cache(command):
    key = command.cr_frame.f_locals['args'][1]

    if not await r.exists([key]):
        result = db.get_collection(key.split(':', 1)[0]).find_one({'_id' : key.split(':', 1)[1]})
        if result == None:
            return None
        value = result['data']
        await redis_any_set(key,value)
    result = await command
    return result

async def main():
    await cache() # ADD A COMMAND HERE TO TEST THE CODE

if '__name__'=='__main__':
    asyncio.run(main())