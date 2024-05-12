import os
import re
import json
import uuid
import base64
import time
import asyncio
import discord
from discord import File
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from descriptor import descriptor 

async def download_character(link):

    download_dir = os.path.abspath("downloaded_images")

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    file_list = set(f for f in os.listdir(download_dir) if not f.endswith('.crdownload') and not f.endswith('.tmp'))

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    driver.get(link)

    # Find the "Export Character" button and click it
    export_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.ant-btn.ant-btn-default.ant-btn-block.ant-dropdown-trigger.mt-4")))
    export_button.click()

    # Wait for the dropdown menu to appear
    dropdown_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-dropdown-menu")))

    # Wait for the "V2 Character Card" option to be interactable
    v2_button_li = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.ant-dropdown-menu-item[data-menu-id*='rc-menu-uuid']")))

    # Click the "V2 Character Card" option using JavaScript
    driver.execute_script("arguments[0].click();", v2_button_li)

    # # Wait for the download to complete
    while set(f for f in os.listdir(download_dir) if not f.endswith('.crdownload') and not f.endswith('.tmp')) == file_list:
        await asyncio.sleep(0.1)

    # Close the browser
    driver.quit()

    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg']

    files = os.listdir(download_dir)
    image_files = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]
    paths = [os.path.join(download_dir, basename) for basename in image_files]

    return max(paths, key=os.path.getmtime) if paths else None

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

FORUM_CHANNEL_ID = 1143741288655622178
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

async def character_post(char_id, r, name, image_path=None, client=None):
    forum_channel = await client.fetch_channel(FORUM_CHANNEL_ID)
    if forum_channel is None:
        print(f"Error: Could not find forum channel with ID {FORUM_CHANNEL_ID}")
        return

    thread_title = f"{name}"
    try:
        # char_data = await r.json.get(f'characters:{char_id}','.data.description')
        char_data = await r.json.get(f'characters:{char_id}','.data.name','.data.description')

        description = re.sub(r'\\{2,}|\n{2,}', '', descriptor(char_data))
    except:
        description = ""
    thread_text = f"{description}\n\n[{char_id}]"

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
        print(f"Created Character Post: {thread.name}")
        message_url = thread.jump_url
        await r.json.set(f'characters:{char_id}', 'postlink', message_url)
        if os.path.exists(image_path):
            os.remove(image_path)
        return message_url
    except discord.HTTPException as e:
        print(f"Error creating thread: {e}")
        return None

async def save_character(r, char_data, json_file, client):
    try:
        chub_id = char_data['data']['extensions']['chub']['id']
    except:
        return None
    if not await r.sismember('chub_id_list', chub_id):
        charID = generate_unique_id()
        while charID < 100000 or await r.sismember('character_id_list', charID):
            charID = generate_unique_id()
        await r.json.set(f'characters:{charID}', '.', char_data)
        await r.hset('chub_to_charID', {chub_id: charID})  # Pass a dict if using Coredis
        await r.sadd('character_id_list', [charID])
        await r.sadd('chub_id_list', [chub_id])

        name = char_data['data']['name']
        image_name = os.path.splitext(json_file)[0]
        image_path = os.path.join('downloaded_images', f'{image_name}.png')

        await character_post(charID, r, name, image_path=image_path, client=client)
        return charID
    else:
        return await r.hget('chub_to_charID', chub_id)

async def import_character_from_link(link, client, r):
    # Download the character
    image_path = await download_character(link)
    metadata = get_character_data(image_path)
    filename = os.path.basename(image_path)

    if metadata is not None:
        json_filename = os.path.splitext(filename)[0] + '.json'
        json_path = os.path.join('converted_jsons', json_filename)

        with open(json_path, 'w') as json_file:
            json.dump(metadata, json_file)

        # Save the character data and create a thread
        char_id = await save_character(r, metadata, json_filename, client)
        if char_id:
            print(f"Imported character with ID: {char_id}")
        else:
            print(f"Immature character requested, aborted.")
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(json_path):
                os.remove(json_path)

        return char_id


async def save_custom_character(r, char_data, userID, image_path, client):
    charID = generate_unique_id()
    while charID < 100000 or await r.sismember('character_id_list', charID):
        charID = generate_unique_id()
    await r.json.set(f'characters:{charID}', '.', char_data)
    await r.sadd(f'users:{userID}:CustomCharacters', [charID])
    await r.sadd('character_id_list', [charID])
    name = char_data['data']['name']
    message_url = await character_post(charID, r, name, image_path=image_path, client=client)
    return message_url
