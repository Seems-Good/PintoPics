import os 
import discord
import aiohttp
from datetime import datetime

# Set discord token as env variable so we can read it here.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# Quick check enviroment var is actually set.
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN enviroment variable not set.")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

'''
this is where all content/media is stored.
common paths look like:
- $api_endpoint/content/petName-0001.jpg
    * not exclusive to .jpg we check the extension dynamicaly 
'''
api_endpoint = 'https://r2-api.seemsgood.org/content'

'''
Each pet may have a different limit (length of indexable photos uploaded)
the 'generic' for our pet data struct looks somthing like:
- petName_limit = len(petName.photos[])
- petName_index = 0
# We start at 0 here so if a user in another server fires event, the index is +1 for *all* servers.
'''
# Pinto globals
pinto_limit = 23
pinto_index = 0 
emote_pintocool = '<:pintocool:1391935318797844500>'
# Ellie globals
ellie_limit = 20
ellie_index = 0
# Murph globals
murph_limit = 20
murph_index = 0

# Event happens after we succesfully auth with discord.api. 
# lets us know the username(bot's username) of token we input by printing to stdout.
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Take a api_endpoint path, petName, and the current index for that pet.
# returns the file extension of the media by sending a http request 
async def find_existing_url(base_url, name,  index):
    extensions = ['jpg', 'png', 'mp4', 'MP4', 'JPG', 'PNG']
    async with aiohttp.ClientSession() as session:
        for ext in extensions:
            url = f'{base_url}/{name}-{index:04}.{ext}'
            async with session.head(url) as resp:
                if resp.status == 200:
                    return url
    return None

@client.event
async def on_message(message):
    # Global Index
    global pinto_index, ellie_index, murph_index
    if message.author == client.user:
        return

    content_lower = message.content.lower()
    timestampNow = datetime.now()
    fmtTime = timestampNow.strftime("[ %I:%M:%S %p - %m-%d-%Y ]")
    whoSent = message.author.display_name

    if "pinto" in content_lower:
        name = "pinto"
        pinto_index = (pinto_index % pinto_limit) + 1
        url = await find_existing_url(api_endpoint, name, pinto_index)
        if url:
            msg = f'{emote_pintocool} Pinto Mentioned {emote_pintocool}'
            print(f'{fmtTime} - [ Soure User: {whoSent} ] - [ Pinto Found ] - [ Calling API: {url} ]')
            await message.channel.send(url, delete_after=60) #delete after 1 min.
            await message.channel.send(msg, delete_after=60) #delete after 1 min.
        else:
            print(f'{fmtTime} - [ Source User: {whoSent} ] - [ Pinto Media Not Found for index {photo_index:04} ]')

    if "ellie" in content_lower:
        name = "ellie"
        ellie_index = (ellie_index % ellie_limit) + 1
        url = await find_existing_url(api_endpoint, name, ellie_index)
        if url:
            print(f'{fmtTime} - [ Source User: {whoSent} ] - [ Ellie Found ] - [ Calling {url} ]')
            await message.channel.send(url, delete_after=60)
            await message.channel.send(f'💖 Ellie Mentioned 💖', delete_after=60)
        else:
            print(f'{fmtTime} - [ Source User: {whoSent} ] - [ Ellie Media Not Found for index {ellie_index:04} ]')

    if "murph" in content_lower:
        name = "murph"
        murph_index = (murph_index % murph_limit) + 1
        url = await find_existing_url(api_endpoint, name, murph_index)
        if url:
            print(f'{fmtTime} - [ Source User: {whoSent} ] - [ Murph Found ] - [ Calling {url} ]')
            await message.channel.send(url, delete_after=60)
            await message.channel.send(f'💖 Murph Mentioned 💖', delete_after=60)
        else:
            print(f'{fmtTime} - [ Source User: {whoSent} ] - [ Murph Media Not Found for index {murph_index:04} ]')


# start discord api client.
client.run(DISCORD_TOKEN)
