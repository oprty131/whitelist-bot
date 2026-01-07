import discord
import os
import requests
import asyncio 
import json
import threading
import time
from discord.ext import commands
from discord import app_commands
from flask import Flask
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

GUILD_ID = 1218339001203818576
ROLE_ID = 1266420174836207717

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

MAPPING_FILE = "mapping.json"
WHITELIST_BACKUP_CHANNEL_ID = 1319770254347599882

def load_mapping():
    if not os.path.isfile(MAPPING_FILE):
        return {}
    with open(MAPPING_FILE, "r") as f:
        return json.load(f)

def save_mapping(data):
    with open(MAPPING_FILE, "w") as f:
        json.dump(data, f, indent=4)

def user_has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)

async def send_backup_file(bot):
    if os.path.exists(MAPPING_FILE):
        channel = bot.get_channel(WHITELIST_BACKUP_CHANNEL_ID)
        if channel:
            await channel.send(file=discord.File(MAPPING_FILE, filename="mapping.json"))

async def auto_restore_database(bot):
    channel = bot.get_channel(WHITELIST_BACKUP_CHANNEL_ID)
    if not channel:
        print("❌ Backup channel not found.")
        return

    messages = [msg async for msg in channel.history(limit=50) if msg.attachments]
    for msg in messages:
        for attachment in msg.attachments:
            if attachment.filename == "mapping.json":
                file_data = await attachment.read()
                with open(MAPPING_FILE, "wb") as f:
                    f.write(file_data)
                print("✅ mapping.json restored on startup.")
                return
    print("⚠️ No recent mapping.json backup found.")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class CustomMessageButtonView(discord.ui.View):
    def __init__(self, message: str):
        super().__init__(timeout=None)
        self.message = message

    @discord.ui.button(label="Send Message", style=discord.ButtonStyle.primary)
    async def send_custom_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(self.message, ephemeral=False)

@bot.event
async def on_ready():
    bot.add_view(KeyPanel())    
    await bot.tree.sync()
    await auto_restore_database(bot)
    print(f"Bot is online as {bot.user}")

previous_status = None

async def check_status():
    global previous_status

    await bot.wait_until_ready()
    channel = bot.get_channel(1302378980019667097)

    while not bot.is_closed():
        try:
            url = "https://downforeveryoneorjustme.com/pythonanywhere.com"
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text().lower()

            if "it's just you" in text:
                current_status = "UP"
            elif "looks down" in text:
                current_status = "DOWN"
            else:
                current_status = "UNKNOWN"

            if current_status != previous_status:
                previous_status = current_status
                await channel.send(f"🔔 **TBO is:** `{current_status}`")

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(60)

FLASK_API = "https://okei.pythonanywhere.com"
BOT_SECRET = "robertmike56"

def is_admin(member):
    return member.guild_permissions.administrator

class KeyPanel(discord.ui.View):
    timeout = None

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.green)
    async def generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = await asyncio.to_thread(
            requests.post,
            f"{FLASK_API}/create_key",
            json={
                "discord_id": str(interaction.user.id),
                "discord_username": interaction.user.name
            },
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=10
        )
        data = r.json()

        if not data.get("ok"):
            await interaction.response.send_message(
                "❌ Failed to generate key",
                ephemeral=True
            )
            return

        key = data["key"]
        script = f'getgenv().Key = "{key}"\nloadstring(game:HttpGet("https://peeky.pythonanywhere.com/jjs"))()'
        await interaction.response.send_message(f"```lua\n{script}\n```", ephemeral=True)

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.red)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = await asyncio.to_thread(
            requests.post,
            f"{FLASK_API}/reset_key",
            json={"discord_id": str(interaction.user.id)},
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=10
        )
        data = r.json()
        if data.get("ok"):
            await interaction.response.send_message("✅ Your HWID has been reset.", ephemeral=True)
        elif data.get("reason") == "cooldown":
            await interaction.response.send_message("⏳ You must wait 24h before resetting again.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Reset failed.", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def setuppanel(ctx):
    embed = discord.Embed(
        title="🔐 Whitelist Panel",
        description="Generate or reset whitelist keys",
        color=0x2B2D31
    )
    await ctx.send(embed=embed, view=KeyPanel())

@bot.tree.command(name="Remove Whitelist", description="Remove a Discord user from the whitelist")
@app_commands.describe(user="The Discord user to remove from whitelist")
@app_commands.default_permissions(administrator=True)
async def removewhitelist(interaction: discord.Interaction, user: discord.Member):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message(
            "❌ This command can only be used in the authorized server.",
            ephemeral=True
        )
        return
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Admins only.",
            ephemeral=True
        )
        return
    try:
        r = await asyncio.to_thread(
            requests.post,
            f"{FLASK_API}/unwhitelist",
            json={"discord_id": str(user.id)},
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=10
        )
        data = r.json()
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed: {e}",
            ephemeral=True
        )
        return

    if data.get("ok"):
        await interaction.response.send_message(
            f"✅ {user.name} has been removed from the whitelist.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Could not remove {user.name} from the whitelist.",
            ephemeral=True
        )
            
@bot.tree.command(name="raidbutton", description="Send a custom message with a button")
@app_commands.describe(message="The message to send when the button is pressed")
async def say_command(interaction: discord.Interaction, message: str):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("❌ This command can only be used in the authorized server.", ephemeral=True)
        return
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not user_has_role(member, ROLE_ID):
        await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
        return

    view = CustomMessageButtonView(message)
    await interaction.response.send_message("Click the button to send your message.", view=view, ephemeral=True)
    
@bot.tree.command(name="codex", description="Latest Codex News")
async def codex(interaction: discord.Interaction):
    channel = bot.get_channel(1402685581691060306)
    await interaction.response.defer(ephemeral=False)

    try:
        async for msg in channel.history(limit=100):
            if "CODEX ANDROID" in msg.content.upper() and "```" in msg.content:
                code_block = msg.content.split("```")[1]
                version_line = next((line for line in code_block.splitlines() if any(char.isdigit() for char in line)), "")
                codex_version = next((word for word in version_line.replace("(", "").replace(")", "").split() if "." in word), None)

                if not codex_version:
                    await interaction.followup.send("❌ No valid version found in changelog.")
                    return

                ios_data = requests.get("https://itunes.apple.com/lookup?id=431946152").json()
                ios_version = ios_data["results"][0]["version"]

                codex_parts = codex_version.strip().split(".")
                ios_parts = ios_version.strip().split(".")

                match = all(
                    codex_parts[i] == ios_parts[i]
                    for i in range(min(len(codex_parts), 4))
                )

                status = "🟢 Codex is Working." if match else "🔴 Codex is Down."
                download_line = "\n# **Download at** https://codex.lol/android" if match else ""

                await interaction.followup.send(f"**{status}**\n```{code_block}```{download_line}")
                return

        await interaction.followup.send("❌ No message containing 'CODEX ANDROID' found.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="delta", description="Latest Delta News")
async def delta(interaction: discord.Interaction):
    channel = bot.get_channel(1402685581691060306)
    await interaction.response.defer(ephemeral=False)

    try:
        delta_android_version = None
        delta_ios_version = None
        android_block = None
        ios_block = None

        async for msg in channel.history(limit=100):
            if "Delta Android Update" in msg.content and "```" in msg.content:
                android_block = msg.content.split("```")[1]
                version_line = next((line for line in android_block.splitlines() if any(char.isdigit() for char in line)), "")
                delta_android_version = next((word for word in version_line.replace("(", "").replace(")", "").split() if "." in word), None)

            if "Delta iOS Update" in msg.content and "```" in msg.content:
                ios_block = msg.content.split("```")[1]
                version_line = next((line for line in ios_block.splitlines() if any(char.isdigit() for char in line)), "")
                delta_ios_version = next((word for word in version_line.replace("(", "").replace(")", "").split() if "." in word), None)

            if delta_android_version and delta_ios_version:
                break

        if not delta_android_version and not delta_ios_version:
            await interaction.followup.send("❌ No Delta Android or iOS updates found.")
            return

        android_status = "🟢 Working" if delta_android_version else "🔴 Down"
        ios_status = "🟢 Working" if delta_ios_version else "🔴 Down"

        android_link = "\n# **Download at** https://deltaexploits.gg/delta-executor-android" if delta_android_version else ""
        ios_link = "\n# **Download at** https://deltaexploits.gg/delta-executor-ios" if delta_ios_version else ""

        await interaction.followup.send(
            f"**Delta Android:** {android_status}{android_link}\n"
            f"**Delta iOS:** {ios_status}{ios_link}\n"
            f"{f'```{android_block}```' if android_block else ''}"
            f"{f'```{ios_block}```' if ios_block else ''}"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

cooldowns = {}

@bot.tree.command(name="snipe", description="Stream Snipe Someone")
@app_commands.describe(user_id="UserID", place_id="PlaceID")
async def snipe(interaction: discord.Interaction, user_id: int, place_id: int):
    user = interaction.user.id
    now = time.time()

    if user in cooldowns and now - cooldowns[user] < 300:
        remaining = 300 - (now - cooldowns[user])
        minutes = round(remaining / 60, 1)
        await interaction.response.send_message(
            f"⏳ Please wait {minutes} minutes before using this command again.",
            ephemeral=True
        )
        return

    cooldowns[user] = now

    await interaction.response.send_message(f"🔍 Searching for user `{user_id}` in place `{place_id}`...", ephemeral=True)

    user_data = requests.get(f"https://users.roblox.com/v1/users/{user_id}").json()
    username = user_data.get("name", "Unknown")
    target_thumb = requests.get(
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    ).json()["data"][0]["imageUrl"]

    cursor = ""
    headers = {"User-Agent": "DiscordBot/1.0"}
    found_servers = []

    embed = discord.Embed(
        title=f"{user_id} | {username}",
        description=f"Place ID: {place_id}\nSearching servers...",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=target_thumb)
    msg = await interaction.followup.send(embed=embed, ephemeral=False)

    while True:
        url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100"
        if cursor:
            url += f"&cursor={cursor}"

        r = requests.get(url, headers=headers)
        data = r.json()
        servers = data.get("data", [])
        if not servers:
            break

        updated = False
        for s in servers:
            tokens = [{"token": t, "type": "AvatarHeadshot", "size": "150x150", "requestId": s["id"]} for t in s.get("playerTokens", [])]
            if not tokens:
                continue
            thumb_data = requests.post(
                "https://thumbnails.roblox.com/v1/batch",
                headers={"Content-Type": "application/json"},
                json=tokens
            ).json()
            for t in thumb_data.get("data", []):
                if t.get("imageUrl") == target_thumb and s["id"] not in found_servers:
                    found_servers.append(s["id"])
                    updated = True

        if updated:
            desc = f"Place ID: {place_id}\nFound in servers:\n"
            for sid in found_servers:
                desc += f"Join: [Click Here To Join](https://peeky.pythonanywhere.com/join?placeId={place_id}&gameInstanceId={sid})\n"
            embed.description = desc
            await msg.edit(embed=embed)

        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        await asyncio.sleep(1.5)

    if not found_servers:
        embed.description = f"Place ID: {place_id}\n❌ Target not found in currently listed servers."
        await msg.edit(embed=embed)

@bot.tree.command(name="whitelist", description="Add a UserId to the whitelist")
@app_commands.describe(userid="UserId to whitelist")
async def whitelist(interaction: discord.Interaction, userid: int):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("❌ This command can only be used in the authorized server.", ephemeral=True)
        return
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not user_has_role(member, ROLE_ID):
        await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
        return

    try:
        discord_id = str(interaction.user.id)
        mapping = load_mapping()
        user_info = requests.get(f"https://users.roblox.com/v1/users/{userid}")
        if user_info.status_code != 200:
            await interaction.response.send_message(f"❌ User ID `{userid}` doesn't exist on Roblox.", ephemeral=True)
            return
        user_data = user_info.json()
        username = user_data["name"]
        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=420&height=420&format=png"

        response = requests.get("https://peeky.pythonanywhere.com/Premium")
        table_code = response.text.strip()
        ids = [int(i.strip()) for i in table_code[table_code.find("{")+1:table_code.find("}")].split(",") if i.strip().isdigit()]

        if discord_id in mapping:
            old_userid = mapping[discord_id]
            if old_userid not in ids:
                pass
            else:
                await interaction.response.send_message("❌ You already have a whitelisted account. Use `/replace`.", ephemeral=True)
                return

        if userid in ids:
            embed = discord.Embed(title="✅ Already Whitelisted", description=f"**{username}** (`{userid}`) is already whitelisted.", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        ids.append(userid)
        updated_table = "return {\n    " + ",\n    ".join(map(str, ids)) + "\n}"
        post_response = requests.post(
            "https://peeky.pythonanywhere.com/edit/Premium",
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-Bypass-Auth": "supersecretbypass123"},
            data={"content": updated_table}
        )

        if post_response.status_code == 200:
            mapping[discord_id] = userid
            save_mapping(mapping)
            await send_backup_file(bot)
            embed = discord.Embed(title="✅ Whitelisted", description=f"**{username}** (`{userid}`) has been added to the whitelist.", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("❌ Failed to update whitelist table.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="loaddatabase", description="Restore mapping.json from latest backup")
async def loaddatabase(interaction: discord.Interaction):
    try:
        channel = bot.get_channel(WHITELIST_BACKUP_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Backup channel not found.", ephemeral=True)
            return

        messages = [msg async for msg in channel.history(limit=50) if msg.attachments]
        for msg in messages:
            for attachment in msg.attachments:
                if attachment.filename == "mapping.json":
                    file_data = await attachment.read()
                    with open(MAPPING_FILE, "wb") as f:
                        f.write(file_data)
                    await interaction.response.send_message("✅ `mapping.json` restored successfully.", ephemeral=False)
                    return

        await interaction.response.send_message("❌ No recent mapping.json backup found.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="replace", description="Replace your whitelisted UserId with a new one")
@app_commands.describe(new_userid="New UserId")
async def replacewhitelist(interaction: discord.Interaction, new_userid: int):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("❌ This command can only be used in the authorized server.", ephemeral=True)
        return
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not user_has_role(member, ROLE_ID):
        await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
        return

    try:
        discord_id = str(interaction.user.id)
        mapping = load_mapping()
        if discord_id not in mapping:
            await interaction.response.send_message("❌ You haven't whitelisted anyone. Use `/whitelist` first.", ephemeral=True)
            return

        old_userid = mapping[discord_id]
        user_info = requests.get(f"https://users.roblox.com/v1/users/{new_userid}")
        if user_info.status_code != 200:
            await interaction.response.send_message(f"❌ User ID `{new_userid}` doesn't exist on Roblox.", ephemeral=True)
            return
        user_data = user_info.json()
        username = user_data["name"]
        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={new_userid}&width=420&height=420&format=png"

        response = requests.get("https://peeky.pythonanywhere.com/Premium")
        table_code = response.text.strip()
        ids = [int(i.strip()) for i in table_code[table_code.find("{")+1:table_code.find("}")].split(",") if i.strip().isdigit()]

        if old_userid not in ids:
            # Old ID no longer exists, allow re-whitelisting
            index = None
        else:
            index = ids.index(old_userid)

        if new_userid not in ids:
            if index is not None:
                ids[index] = new_userid
            else:
                ids.append(new_userid)
        else:
            if index is not None:
                ids.pop(index)

        updated_table = "return {\n    " + ",\n    ".join(map(str, ids)) + "\n}"
        post_response = requests.post(
            "https://peeky.pythonanywhere.com/edit/Premium",
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-Bypass-Auth": "supersecretbypass123"},
            data={"content": updated_table}
        )

        if post_response.status_code == 200:
            mapping[discord_id] = new_userid
            save_mapping(mapping)
            await send_backup_file(bot)
            embed = discord.Embed(title="✅ Replaced", description=f"Replaced with **{username}** (`{new_userid}`).", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)  # Thumbnail instead of embed image
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("❌ Failed to update table.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="check", description="Check your whitelisted account")
async def check(interaction: discord.Interaction):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("❌ This command can only be used in the authorized server.", ephemeral=True)
        return
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not user_has_role(member, ROLE_ID):
        await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
        return

    try:
        discord_id = str(interaction.user.id)
        mapping = load_mapping()
        if discord_id not in mapping:
            await interaction.response.send_message("❌ You are not whitelisted.", ephemeral=True)
            return

        userid = mapping[discord_id]
        user_info = requests.get(f"https://users.roblox.com/v1/users/{userid}")
        if user_info.status_code != 200:
            await interaction.response.send_message("❌ This UserId doesn't exist.", ephemeral=True)
            return
        user_data = user_info.json()
        username = user_data["name"]
        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=420&height=420&format=png"

        embed = discord.Embed(title="Whitelisted Account", description=f"**{username}** (`{userid}`)", color=0x00FF00)
        embed.set_thumbnail(url=avatar_url)
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

token = os.getenv("TOKEN")
if not token:
    raise ValueError("TOKEN not set in .env.")

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()
bot.run(token)
