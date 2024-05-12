def connected(database:str):
    # Define the box-drawing characters
    top_left = "\u250C"
    top_right = "\u2510"
    bottom_left = "\u2514"
    bottom_right = "\u2518"
    horizontal = "\u2500"
    vertical = "\u2502"

    # Define the text to be printed
    text = f"{database} CONNECTION ESTABLISHED"

    # Calculate the width of the box
    width = len(text) + 4  # Add 6 for the box outline and padding

    # Print the top of the box
    print(f"\033[1;92m{top_left}{horizontal * (width - 2)}{top_right}\033[00m")

    # Print the text line with padding
    print(f"\033[1;92m{vertical} {text} {vertical}\033[00m")

    # Print the bottom of the box
    print(f"\033[1;92m{bottom_left}{horizontal * (width - 2)}{bottom_right}\033[00m")

def disconnected(database:str):
    # Define the box-drawing characters
    top_left = "\u250C"
    top_right = "\u2510"
    bottom_left = "\u2514"
    bottom_right = "\u2518"
    horizontal = "\u2500"
    vertical = "\u2502"

    # Define the text to be printed
    text = f"⚠  {database} CONNECTION FAILURE"

    # Calculate the width of the box
    width = len(text) + 4  # Add 6 for the box outline and padding

    # Print the top of the box
    print(f"\033[1;91m{top_left}{horizontal * (width - 2)}{top_right}\033[00m")

    # Print the text line with padding
    print(f"\033[1;91m{vertical} {text} {vertical}\033[00m")

    # Print the bottom of the box
    print(f"\033[1;91m{bottom_left}{horizontal * (width - 2)}{bottom_right}\033[00m")


async def check(r,db):
    try:
        await r.ping()
        connected('REDIS')
    except coredis.exceptions.ConnectionError:
        disconnected('REDIS')

    try:
        db.get_collections()
        connected('ASTRADB')
    except:
        disconnected('ASTRADB')