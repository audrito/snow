import os
from dotenv import load_dotenv
import coredis
from astrapy import DataAPIClient

load_dotenv()

# r = coredis.Redis(host='localhost', port=6379, decode_responses=True)    # Local Database For Testing

r = coredis.Redis(host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT"), password=os.environ.get("REDIS_PASSWORD"), db=0, decode_responses=True)

db = DataAPIClient(os.environ.get("ASTRA_DB_APPLICATION_TOKEN")).get_database_by_api_endpoint(
    os.environ.get("ASTRA_DB_API_ENDPOINT"),
    namespace="default_keyspace"
)

# Could be removed after shifting to chatmodels completely.

# redis_password = os.environ.get("REDIS_PASSWORD")
# redis_host = os.environ.get("REDIS_HOST")
# redis_port = os.environ.get("REDIS_PORT")
# redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"


SCAN = 4 * 60

EXPIRE = 13 * 60