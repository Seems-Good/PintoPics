import os
import discord
import aiohttp
import boto3
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# ---- CONFIG ----
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_BUCKET = "r2-pintopics"
API_ENDPOINT = "https://r2-api.seemsgood.org/content"
# ---- DISCORD SETUP ----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
# ---- R2 CLIENT ----
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)
# ---- PET STATE ----
DEFAULT_EMOTE = "🐾"
pets = {
    "pinto": {"index": 0, "limit": 0, "emote": "<:pintocool:1391935318797844500>"},
    "ellie": {"index": 0, "limit": 0, "emote": "<:ellie:1399190760259194951>"},
    "murph": {"index": 0, "limit": 0, "emote": "<:murph:1399190806018916403>"},
}

# ---- R2 STORAGE ----
async def find_existing_url(base_url, name, index):
    """Check if file exists at URL with known extensions."""
    extensions = ["jpg", "png", "jpeg", "gif", "mp4", "mov"]
    extensions += [e.upper() for e in extensions]  # uppercase variants
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
        data["index"] = 0
    print("Pet limits updated:", {k: v["limit"] for k, v in pets.items()})

# ---- SLASH COMMAND ----
@bot.tree.command(name="add", description="Upload a  pet to use with PintoPics (images, gifs, and videos supported)")
@app_commands.describe(name="Pet name", media="The image/video to upload (jpg/png/gif/mp4/mov/mkv)")
async def add(interaction: discord.Interaction, name: str, media: discord.Attachment):
    name = name.lower()
    if name not in pets:
        pets[name] = {"index": 0, "limit": 0, "emote": DEFAULT_EMOTE}

    await interaction.response.defer(ephemeral=True)

    ext = os.path.splitext(media.filename)[1].lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".mkv"}
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

    # Update pet limits after upload
    await populate_pet_limits()

    await interaction.followup.send(f"✅ Uploaded `{key}` to R2 successfully!", ephemeral=True)

# ---- MESSAGE LISTENER ----
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    whoSent = message.author.display_name
    timestampNow = datetime.now().strftime("[ %I:%M:%S %p - %m-%d-%Y ]")

    for word in content_lower.split():
        pet_name = word.strip()
        if not pet_name:
            continue

        if pet_name not in pets:
            # Add new pet dynamically
            pets[pet_name] = {"index": 0, "limit": 0, "emote": DEFAULT_EMOTE}
            await populate_pet_limits()

        data = pets[pet_name]
        if data["limit"] == 0:
            print(f"{timestampNow} - [ User: {whoSent} ] - [ {pet_name} No media uploaded yet ]")
            continue

        # Rotate index
        data["index"] = (data["index"] % data["limit"]) + 1
        url = await find_existing_url(API_ENDPOINT, pet_name, data["index"])
        if url:
            print(f"{timestampNow} - [ User: {whoSent} ] - [ {pet_name} Found ] - [ {url} ]")
            await message.channel.send(url, delete_after=60)
            await message.channel.send(
                f'{data["emote"]} {pet_name.capitalize()} Mentioned {data["emote"]}',
                delete_after=60,
            )

# ---- STARTUP ----
@bot.event
async def on_ready():
    await bot.tree.sync()
    await populate_pet_limits()
    print(f"✅ Logged in as {bot.user}")

bot.run(DISCORD_TOKEN)
