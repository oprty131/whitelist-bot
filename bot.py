import discord
import os
import requests
import json
import threading
from discord.ext import commands
from discord import app_commands
from flask import Flask
from dotenv import load_dotenv

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
    await bot.tree.sync()
    await auto_restore_database(bot)
    print(f"Bot is online as {bot.user}")

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
        if discord_id in mapping:
            await interaction.response.send_message("❌ You already have a whitelisted account. Use `/replace`.", ephemeral=True)
            return

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

        if userid in ids:
            embed = discord.Embed(title="✅ Already Whitelisted", description=f"**{username}** (`{userid}`) is already whitelisted.", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        ids.append(userid)
        updated_table = "return {\n    " + ",\n    ".join(map(str, ids)) + "\n}"
        post_response = requests.post("https://peeky.pythonanywhere.com/edit/Premium", headers={"Content-Type": "application/x-www-form-urlencoded", "X-Bypass-Auth": "supersecretbypass123"}, data={"content": updated_table})

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

@bot.tree.command(name="LoadDatabase", description="Restore mapping.json from latest backup")
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
            await interaction.response.send_message("❌ Your previous ID is no longer in the whitelist.", ephemeral=True)
            return

        index = ids.index(old_userid)
        if new_userid not in ids:
            ids[index] = new_userid
        else:
            ids.pop(index)

        updated_table = "return {\n    " + ",\n    ".join(map(str, ids)) + "\n}"
        post_response = requests.post("https://peeky.pythonanywhere.com/edit/Premium", headers={"Content-Type": "application/x-www-form-urlencoded", "X-Bypass-Auth": "supersecretbypass123"}, data={"content": updated_table})

        if post_response.status_code == 200:
            mapping[discord_id] = new_userid
            save_mapping(mapping)
            await send_backup_file(bot)
            embed = discord.Embed(title="✅ Replaced", description=f"Replaced with **{username}** (`{new_userid}`).", color=0x00FF00)
            embed.set_image(url=avatar_url)
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
            await interaction.response.send_message("❌ This UserId doesn't exists.", ephemeral=True)
            return
        user_data = user_info.json()
        username = user_data["name"]
        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=420&height=420&format=png"

        embed = discord.Embed(title="Whitelisted Account", description=f"**{username}** (`{userid}`)", color=0x00FF00)
        embed.set_image(url=avatar_url)
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

token = os.getenv("TOKEN")
if not token:
    raise ValueError("TOKEN not set in .env.")

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()
bot.run(token)
