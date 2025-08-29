import os
import json
import discord
import aiohttp
import boto3
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo

# ---- CONFIG ----
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") 
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY") 
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY") 
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID") 
R2_BUCKET = "r2-pintopics"
API_ENDPOINT = "https://r2-api.seemsgood.org/content"
PET_JSON_KEY = "pets.json"
BLACKLIST_KEY = "blacklist.json"
LOCAL_TZ = ZoneInfo("America/New_York")
ADMIN_USERS = {".shodo"}  # admin list for admin commands
DEFAULT_EMOTE = "🐾"

# ---- DISCORD SETUP ----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- R2/S3 CLIENT ----
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ---- JSON STATE ----
pets = {}  # Will be loaded from JSON
blacklist = set() # Will be loaded from JSON

# ---- TIMEZONE ----
def get_timestamp():
    return datetime.now(LOCAL_TZ).strftime("[ %I:%M:%S %p - %m-%d-%Y ]")

# ---- R2/S3 STORAGE ----
def save_pets_to_r2():
    """Upload current pets dict to R2 as JSON."""
    pets_bytes = json.dumps(pets, indent=2).encode("utf-8")
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=PET_JSON_KEY,
        Body=pets_bytes,
        ContentType="application/json"
    )

def load_pets_from_r2():
    """Load pets dict from R2, or create defaults if missing."""
    global pets
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=PET_JSON_KEY)
        pets_bytes = response["Body"].read()
        pets = json.loads(pets_bytes)
    except s3.exceptions.NoSuchKey:
        # Default pets
        pets = {
            "pinto": {"emote": "<:pintocool:1391935318797844500>", "limit": 0, "index": 0},
            "ellie": {"emote": "<:ellie:1399190760259194951>", "limit": 0, "index": 0},
            "murph": {"emote": "<:murph:1399190806018916403>", "limit": 0, "index": 0},
        }
        save_pets_to_r2()

def load_blacklist_from_r2():
    global blacklist
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=BLACKLIST_KEY)
        data_bytes = response["Body"].read()
        data_list = json.loads(data_bytes)
        blacklist = set(data_list)
    except s3.exceptions.NoSuchKey:
        blacklist = set()
        save_blacklist_to_r2()

def save_blacklist_to_r2():
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=BLACKLIST_KEY,
        Body=json.dumps(list(blacklist), indent=2).encode("utf-8"),
        ContentType="application/json",
    )

async def find_existing_url(base_url, name, index):
    """Check if file exists at URL with known extensions."""
    extensions = ["jpg", "png", "jpeg", "gif", "mp4", "mov"]
    extensions += [e.upper() for e in extensions]
    async with aiohttp.ClientSession() as session:
        for ext in extensions:
            url = f"{base_url}/{name}-{index:04}.{ext}"
            async with session.head(url) as resp:
                if resp.status == 200:
                    return url
    return None

def get_next_index(name: str, ext: str) -> str:
    """Find next available index for a pet in R2 by listing objects."""
    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"content/{name}-")
    existing = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.startswith(f"content/{name}-"):
            try:
                idx = int(key.split("-")[-1].split(".")[0])
                existing.append(idx)
            except ValueError:
                continue
    next_index = max(existing) + 1 if existing else 1
    return f"content/{name}-{next_index:04}{ext}"

async def populate_pet_limits():
    """Scan R2 bucket and set the limit for each pet automatically."""
    for pet_name, data in pets.items():
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"content/{pet_name}-")
        if "Contents" in response:
            data["limit"] = len(response["Contents"])
        else:
            data["limit"] = 0
        if "index" not in data:
            data["index"] = 0
    print("📊 Pet limits updated:", {k: v["limit"] for k, v in pets.items()})
    save_pets_to_r2()

###########################
# ---- USER COMMANDS ---- #
###########################
# ---- /add $name $media_file - add new content for a pet or create a new one. ----
@bot.tree.command(name="add", description="Upload a file for a pet (images/videos supported)")
@app_commands.describe(name="Pet name", media="The file to upload (jpg/png/gif/mp4/mov)")
async def add(interaction: discord.Interaction, name: str, media: discord.Attachment):
    name = name.lower()
    if name not in pets:
        pets[name] = {"index": 0, "limit": 0, "emote": DEFAULT_EMOTE}
        save_pets_to_r2() 
    await interaction.response.defer(ephemeral=True)
    ext = os.path.splitext(media.filename)[1].lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"}
    allowed_mimes = {"video/mp4", "video/quicktime"}
    is_allowed = media.content_type.startswith("image/") or media.content_type in allowed_mimes or ext in allowed_exts
    if not is_allowed:
        await interaction.followup.send(
            "❌ Invalid file type. Allowed: jpg, png, gif, mp4, mov", ephemeral=True
        )
        return
    file_bytes = await media.read()
    key = get_next_index(name, ext)
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=media.content_type or "application/octet-stream",
    )
    await populate_pet_limits()
    await interaction.followup.send(f"✅ Uploaded `{key}` to R2 successfully!", ephemeral=True)

# ---- /listpets - list all known pets in pets.json. ----
@bot.tree.command(name="listpets", description="List all registered pets and their emoji")
async def listpets(interaction: discord.Interaction):
    if not pets:
        await interaction.response.send_message("No pets registered yet.", ephemeral=True)
        return
    msg = "\n".join(f"{data['emote']} {name}" for name, data in pets.items())
    await interaction.response.send_message(f"📋 **Registered Pets:**\n{msg}", ephemeral=True)

############################
# ---- ADMIN COMMANDS ---- #
############################
# ---- MANAGE CONTENT ----
@bot.tree.command(name="addemote", description="Set the emote for a pet")
async def addemote(interaction: discord.Interaction, pet_name: str, emoji: str):
    # Only allow admins 
    if interaction.user.display_name not in ADMIN_USERS:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return
    pet_name = pet_name.lower()
    # If pet doesn't exist, create it
    if pet_name not in pets:
        pets[pet_name] = {
            "emote": emoji,
            "limit": 0,
            "index": 0
        }
    else:
        # overwrite directly
        pets[pet_name]["emote"] = emoji 
    save_pets_to_r2()
    msg = f"{get_timestamp()} Set emote for '{pet_name}' to {emoji}."
    await interaction.response.send_message(msg, ephemeral=True)
    print(msg)

# ---- BLACKLIST ADD ----
@bot.tree.command(name="blacklist_add", description="Add a word to the blacklist")
@app_commands.describe(word="The word to blacklist")
async def blacklist_add(interaction: discord.Interaction, word: str):
    if interaction.user.display_name not in ADMIN_USERS:
        await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)
        return
    word = word.lower()
    if word in blacklist:
        await interaction.response.send_message(f"⚠️ '{word}' is already blacklisted.", ephemeral=True)
        return
    blacklist.add(word)
    save_blacklist_to_r2()
    await interaction.response.send_message(f"✅ '{word}' added to blacklist.", ephemeral=True)

# ---- BLACKLIST REMOVE ----
@bot.tree.command(name="blacklist_remove", description="Remove a word from the blacklist")
@app_commands.describe(word="The word to remove from blacklist")
async def blacklist_remove(interaction: discord.Interaction, word: str):
    if interaction.user.display_name not in ADMIN_USERS:
        await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)
        return
    word = word.lower()
    if word not in blacklist:
        await interaction.response.send_message(f"⚠️ '{word}' is not in the blacklist.", ephemeral=True)
        return
    blacklist.remove(word)
    save_blacklist_to_r2()
    await interaction.response.send_message(f"✅ '{word}' removed from blacklist.", ephemeral=True)
    
############################
# ---- EVENT LISTENER ---- #
############################
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    content_lower = message.content.lower()
    whoSent = message.author.display_name
    if any(word in content_lower for word in blacklist):
        return
    for pet_name, data in pets.items():
        if pet_name in content_lower:
            if data["limit"] == 0:
                print(f"{get_timestamp()} - [ User: {whoSent} ] - [ {pet_name} No media uploaded yet ]")
                continue
            # Rotate index
            data["index"] = (data["index"] % data["limit"]) + 1
            url = await find_existing_url(API_ENDPOINT, pet_name, data["index"])
            if url:
                print(f"{get_timestamp()} - [ User: {whoSent} ] - [ {pet_name} Found ] - [ {url} ]")
                await message.channel.send(url, delete_after=60)
                await message.channel.send(
                    f'{data["emote"]} {pet_name.capitalize()} Mentioned {data["emote"]}',
                    delete_after=60,
                )

#################
# --- MAIN ---- #
#################
@bot.event
async def on_ready():
    load_pets_from_r2()
    load_blacklist_from_r2()
    await populate_pet_limits()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

######################################
# ---- START DISCORD API CLIENT ---- #
######################################
bot.run(DISCORD_TOKEN)
