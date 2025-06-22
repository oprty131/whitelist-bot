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

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === Data Files ===
MAPPING_FILE = "mapping.json"

def load_mapping():
    if not os.path.isfile(MAPPING_FILE):
        return {}
    with open(MAPPING_FILE, "r") as f:
        return json.load(f)

def save_mapping(data):
    with open(MAPPING_FILE, "w") as f:
        json.dump(data, f, indent=4)

intents = discord.Intents.default()
intents.message_content = True
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
    print(f"Bot is online as {bot.user}")

@bot.tree.command(name="raidbutton", description="Send a custom message with a button")
@app_commands.describe(message="The message to send when the button is pressed")
async def say_command(interaction: discord.Interaction, message: str):
    view = CustomMessageButtonView(message)
    await interaction.response.send_message("Click the button to send your message.", view=view, ephemeral=True)

@bot.tree.command(name="whitelist", description="Add a UserId to the whitelist")
@app_commands.describe(userid="UserId to whitelist")
async def whitelist(interaction: discord.Interaction, userid: int):
    try:
        discord_id = str(interaction.user.id)
        mapping = load_mapping()
        if discord_id in mapping:
            await interaction.response.send_message("❌ You already whitelisted a Roblox user. Use `/replacewhitelist`.", ephemeral=True)
            return

        user_info = requests.get(f"https://users.roblox.com/v1/users/{userid}")
        if user_info.status_code != 200:
            await interaction.response.send_message(f"❌ User ID `{userid}` doesn't exist on Roblox.", ephemeral=True)
            return
        user_data = user_info.json()
        username = user_data["name"]
        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=420&height=420&format=png"

        response = requests.get("https://peeky.pythonanywhere.com/UserIdTestTable")
        table_code = response.text.strip()
        ids = [int(i.strip()) for i in table_code[table_code.find("{")+1:table_code.find("}")].split(",") if i.strip().isdigit()]

        if userid in ids:
            embed = discord.Embed(title="✅ Already Whitelisted", description=f"**{username}** (`{userid}`) is already whitelisted.", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        ids.append(userid)
        updated_table = "return {\n    " + ",\n    ".join(map(str, ids)) + "\n}"
        post_response = requests.post("https://peeky.pythonanywhere.com/edit/UserIdTestTable", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={"content": updated_table})

        if post_response.status_code == 200:
            mapping[discord_id] = userid
            save_mapping(mapping)
            embed = discord.Embed(title="✅ Whitelisted", description=f"**{username}** (`{userid}`) has been added to the whitelist.", color=0x00FF00)
            embed.set_thumbnail(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("❌ Failed to update whitelist table.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="replace", description="Replace your whitelisted UserId with a new one")
@app_commands.describe(new_userid="New UserId")
async def replacewhitelist(interaction: discord.Interaction, new_userid: int):
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

        response = requests.get("https://peeky.pythonanywhere.com/UserIdTestTable")
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
        post_response = requests.post("https://peeky.pythonanywhere.com/edit/UserIdTestTable", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={"content": updated_table})

        if post_response.status_code == 200:
            mapping[discord_id] = new_userid
            save_mapping(mapping)
            embed = discord.Embed(title="✅ Replaced", description=f"Replaced with **{username}** (`{new_userid}`).", color=0x00FF00)
            embed.set_image(url=avatar_url)
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("❌ Failed to update table.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="check", description="Check your whitelisted account")
async def check(interaction: discord.Interaction):
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
