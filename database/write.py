from database.database import *
import asyncio
import time
from collections import deque
from astrapy.operations import ReplaceOne

async def redis_any_get(key: str, return_type: bool=None):
    """Redis any get is a function to retrieve the value of a key regardless of it's data type with a single function call using a bunch of if/else conditionals under the hood.
    Arguments :
    key: str = The key of the document to retrieve.
    return_type: bool = Returns a tuple containing the value and the type.
    """
    key_type = await r.type(key)

    if key_type == "None":
        print(f'{key} DOES NOT EXIST IN REDIS, DATA LOSS RISK ALERT!')
    elif key_type == "list":
        value = await r.lrange(key, 0, -1)
    elif key_type == "hash":
        value = await r.hgetall(key)
    elif key_type == "ReJSON-RL":
        value = await r.json.get(key)
    elif key_type == "set":
        value = await r.smembers(key)
    elif key_type == "zset":
        value = await r.zrange(key, 0, -1, withscores=True)
    elif key_type == "string":
        value = await r.get(key)
    else:
        raise ValueError(f"Unsupported data type for key '{key}': {key_type}")

    if return_type == True:
        return value,return_type
    else:
        return value


# Function to persist data to AstraDB
async def write_to_astra(keys_and_values, db=db):
    try:
        # Create a list of operations to be performed in bulk
        operations = []
        for key, value in keys_and_values:
            operations.append(ReplaceOne({"_id": key.split(':', 1)[1]}, {"data": value}, upsert=True))

        # Perform the bulk write operation
        db.get_collection(key.split(':', 1)[0]).bulk_write(operations, ordered=False)
    except Exception as e:
        print(f"Error persisting data to AstraDB: {e}")

# SCAN Logic
async def scan_expiring_keys(threshold=420):  # threshold = 7 minutes
    while True:
        # Queue for batching writes
        write_queue = deque()
        cursor = "0"
        keys_to_write = []
        dying_keys_to_write = []
        while cursor != 0:
            cursor, keys = await r.scan(cursor=cursor)
            for key in keys:
                # Get the TTL for the key
                ttl = await r.ttl(key)
                if ttl > 0 and ttl <= threshold:
                    keys_to_write.append(key)

        # Bulk write keys with TTL under 5 minutes
        if len(keys_to_write) >= 120:
            for key in keys_to_write:
                # Retrieve the value for the key
                value = await redis_any_get(key)
                if value:
                    # Add the key-value pair to the write queue
                    write_queue.append((key, value))

        # Bulk write keys with TTL under 1 minute
        elif len(keys_to_write) >= 40:
            for key in keys_to_write:
                if await r.ttl(key) <= 250:
                    dying_keys_to_write.append(key)
            if len(dying_keys_to_write) >= 20:
                for key in dying_keys_to_write:
                    # Retrieve the value for the key
                    value = await redis_any_get(key)
                    if value:
                        # Add the key-value pair to the write queue
                        write_queue.append((key, value))

        # Set 5 minutes TTL for all keys
        else:
            if dying_keys_to_write:
                for key in dying_keys_to_write:
                    await r.expire(key, 300)  # 5 minutes

        # Sleep for a while before the next scan
        await batch_requests(write_queue)
        await asyncio.sleep(240)  # sleep for 4 minutes
        print("DEBUG MESSAGE : ONE SCAN COMPLETE")

async def batch_requests(write_queue):
    if write_queue:
        # Batch size for AstraDB (maximum 20 documents)
        batch_size = 20
        
        # Deque and process batches of size batch_size
        while write_queue:
            batch = [write_queue.popleft() for _ in range(min(len(write_queue), batch_size))]
            await write_to_astra(batch)

async def permanent_delete(command):
    key = command.cr_frame.f_locals['args'][1]
    try:
        db.get_collection(key.split(':', 1)[0]).delete_one({'_id' : key.split(':', 1)[1]})
    except:
        pass
    try:
        await command
    except:
        pass
    return

async def main():
        await scan_expiring_keys()

if __name__ == "__main__":
    asyncio.run(main())