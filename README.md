# PintoPics
A lightweight Discord bot that automatically responds with pictures of pets when their names are mentioned in chat.

---

## Features

- 🐰 Responds to **Pinto** the bunny
- 🐶 Responds to **Ellie** the Shiba Inu
- More to come!!
- ⏱ Deletes messages after 1 minute to reduce clutter
- 🌐 Pulls media dynamically from a remote image API
- 🔒 Docker- and environment-variable-friendly for secure token handling

---

## Example

If you're chatting in a server where PintoPics is active:

```text
User1:
  hey guys i'll be on in a bit i need to take ellie for a walk

PintoPics:
  [Image of Ellie the Shiba Dog](https://r2-api.seemsgood.org/content/ellie-0001.png)
  💖 Ellie Mentioned 💖

User2:
  wow she is so cute!!

User3:
  OMG!! so cute
```

---

## Getting Started

### Requirements

- Python 3.10+
- The following pip packages:
    - aiohttp (for parsing http headers)
    - discord.py
- Discord bot token
- (Optional) Docker

### Running Locally

1. Clone the repo:
   ```bash
   git clone 
   cd PintoPics
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your bot token:
   ```bash
   export DISCORD_TOKEN=your_bot_token_here
   ```

4. Run the bot:
   ```bash
   python3 main.py
   ```

---

## 🐳 Docker Support

### Build and run:

```bash
docker build -t pintopics-app .
docker run -e DISCORD_TOKEN=your_bot_token pintopics-app
```

Or use a `.env` file:

```env
DISCORD_TOKEN=your_bot_token
```

Then:

```bash
docker run --env-file .env pintopics-app
```

---

## TODO / Ideas

- Add spam cooldown to prevent repeated image spam
- Support per-server pet indexes
- Add `!listpets` command
- Allow `author == pet_owner` filtering for exclusivity

---

## License

MIT — free to use, modify, and share!
