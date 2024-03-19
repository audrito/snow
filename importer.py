import os
import json
import uuid
import base64
import time
import redis
import discord
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from discord import File

# Downloader code
def download_character(link):
    # Set up Chrome options
    download_dir = os.path.abspath("downloaded_images")
    os.makedirs(download_dir, exist_ok=True)
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(link)

    # Find the download button and click it
    download_button = driver.find_element(By.XPATH, "//button[contains(.,'V2')]")
    download_button.click()

    # Wait for the download to complete (adjust the sleep time as needed)
    time.sleep(2)

    # Close the browser
    driver.quit()

# Extracter code
def get_character_data(image_path):
    # Open the image file
    with Image.open(image_path) as img:
        # Get the metadata
        metadata = img.info

    # Check if 'chara' is in the metadata
    if 'chara' in metadata:
        # Decode the Base64 encoded JSON string
        chara_json = json.loads(base64.b64decode(metadata['chara']).decode('utf-8'))
        return chara_json
    else:
        print(f'The provided image is either corrupted or not a character card.')
        return None

# Uploader code
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
client = discord.Client(intents=intents)

FORUM_CHANNEL_ID = 1214559209593511936
def generate_unique_id():
    # Generate a UUID version 1
    uuid_obj = uuid.uuid1()

    # Extract the timestamp and node components from the UUID
    time_bytes = uuid_obj.bytes[:6]
    node_bytes = uuid_obj.bytes[6:10]

    # Convert the components to integers
    time_int = int.from_bytes(time_bytes, byteorder='big')
    node_int = int.from_bytes(node_bytes, byteorder='big')

    # Combine the timestamp and node components into a single integer
    unique_id = (time_int << 40) | node_int

    return unique_id % 1000000

async def character_post(char_id, name, image_path=None, client=None):
    forum_channel = await client.fetch_channel(FORUM_CHANNEL_ID)
    if forum_channel is None:
        print(f"Error: Could not find forum channel with ID {FORUM_CHANNEL_ID}")
        return

    thread_title = f"{name}"
    thread_text = f"[{char_id}]"

    message_params = {
        "name": thread_title,
        "content": thread_text
    }

    if image_path:
        image_file = File(image_path)
        message_params["files"] = [image_file]

    try:
        thread_with_message = await forum_channel.create_thread(**message_params)
        thread = thread_with_message.thread
        print(f"Created thread: {thread.name}")
    except discord.HTTPException as e:
        print(f"Error creating thread: {e}")

async def save_character(r, char_data, json_file, client):
    if not await r.sismember('chub_id_list', char_data['data']['extensions']['chub']['id']):
        charID = generate_unique_id()
        while charID < 100000 or await r.sismember('character_id_list', charID):
            charID = generate_unique_id()
        await r.json.set(f'character:{charID}', '.', char_data)
        await r.hset('chub_to_charID', {char_data['data']['extensions']['chub']['id']: charID})  # Pass a dict if using Coredis
        await r.sadd('character_id_list', [charID])
        await r.sadd('chub_id_list', [char_data['data']['extensions']['chub']['id']])

        name = char_data['data']['name']
        image_name = os.path.splitext(json_file)[0]
        image_path = os.path.join('downloaded_images', f'{image_name}.png')

        await character_post(charID, name, image_path=image_path, client=client)
        return charID
    else:
        return await r.hget('chub_to_charID', char_data['data']['extensions']['chub']['id'])

async def import_character_from_link(link, client, r):
    # Download the character
    download_character(link)

    # Process the downloaded image
    for filename in os.listdir('downloaded_images'):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            image_path = os.path.join('downloaded_images', filename)
            metadata = get_character_data(image_path)

            if metadata is not None:
                json_filename = os.path.splitext(filename)[0] + '.json'
                json_path = os.path.join('converted_jsons', json_filename)

                with open(json_path, 'w') as json_file:
                    json.dump(metadata, json_file)

                # Save the character data and create a thread
                char_id = await save_character(r, metadata, json_filename, client)
                print(f"Imported character with ID: {char_id}")

redis_password = os.environ.get("REDIS_PASSWORD")
redis_host = 'redis-13761.c1.us-central1-2.gce.cloud.redislabs.com'
redis_port = 13761

r = redis.Redis(host=redis_host, port=redis_port, db=0, password=redis_password, decode_responses=True)