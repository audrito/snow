import os
from dotenv import load_dotenv
import coredis
from astrapy import DataAPIClient

load_dotenv()

# r = coredis.Redis(host='localhost', port=6379, decode_responses=True)    # Local Database For Testing

REDIS_HOST = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com'
REDIS_PORT = 13761
REDIS_PASSWORD = sys.argv[3]


r = coredis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=0, decode_responses=True)

ASTRA_DB_APPLICATION_TOKEN = sys.argv[4]
ASTRA_DB_API_ENDPOINT = 'https://64f4c8a3-8a5e-4372-b7a4-c2e60ac675c0-us-east-1.apps.astra.datastax.com'

db = DataAPIClient(ASTRA_DB_APPLICATION_TOKEN).get_database_by_api_endpoint(
    ASTRA_DB_API_ENDPOINT,
    namespace="default_keyspace"
)

SCAN = 4 * 60

EXPIRE = 13 * 60
