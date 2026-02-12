import discord
from discord import app_commands
from discord.ext import commands
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
from keepalive import keep_alive

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# helper to get db connection
def get_db():
    return psycopg2.connect(DATABASE_URL)

# db setup
def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # memories table
    c.execute('''CREATE TABLE IF NOT EXISTS memories
                 (id SERIAL PRIMARY KEY, guild_id BIGINT, content TEXT, 
                  image_url TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # date ideas table
    c.execute('''CREATE TABLE IF NOT EXISTS date_ideas
                 (id SERIAL PRIMARY KEY, guild_id BIGINT, idea TEXT, category TEXT, completed BOOLEAN DEFAULT FALSE)''')
                 
    # milestones table
    c.execute('''CREATE TABLE IF NOT EXISTS milestones
                 (id SERIAL PRIMARY KEY, guild_id BIGINT, event_name TEXT, event_date TEXT)''')
    
    conn.commit()
    conn.close()

# bot setup
class Client(commands.Bot):
    def __init__(self):
        # need message content intent for this to work right
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        # only uncomment this line if you added a new command
        # await self.tree.sync() 
        print("Bot is ready! (Skipped syncing to save time)")

    async def on_ready(self):
        init_db()
        print(f'{self.user} is online and database is ready!')

client = Client()

# --- COMMANDS ---

# log command
@client.tree.command(name="log", description="Save a memory to the scrapbook")
@app_commands.describe(memory="The text to remember", image="Optional image to attach")
async def log(interaction: discord.Interaction, memory: str = None, image: discord.Attachment = None):
    image_url = image.url if image else None
    
    if not memory and not image_url:
        await interaction.response.send_message("Please provide text or attach an image.", ephemeral=True)
        return

    conn = get_db()
    c = conn.cursor()
    # postgres uses %s instead of ?
    c.execute("INSERT INTO memories (guild_id, content, image_url) VALUES (%s, %s, %s)", 
              (interaction.guild_id, memory, image_url))
    conn.commit()
    conn.close()
    
    await interaction.response.send_message("Memory logged to the scrapbook.")

# remember command
@client.tree.command(name="remember", description="Recall a random memory")
async def remember(interaction: discord.Interaction):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT content, image_url, date_added FROM memories WHERE guild_id = %s ORDER BY RANDOM() LIMIT 1", (interaction.guild_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        content, image_url, date = row
        desc = content if content else "Image Memory"
        
        embed = discord.Embed(title="Memory Lane", description=desc, color=0xeee657)
        # convert timestamp to string for footer
        embed.set_footer(text=f"Saved on {str(date)[:10]}")
        if image_url:
            embed.set_image(url=image_url)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No memories found.")

# date command (splits category and idea into two fields automatically)
@client.tree.command(name="date", description="Add a new date idea")
@app_commands.describe(category="Type (e.g., Food)", idea="The actual date activity")
async def date(interaction: discord.Interaction, category: str, idea: str):
    category = category.strip().title()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO date_ideas (guild_id, idea, category) VALUES (%s, %s, %s)", 
              (interaction.guild_id, idea, category))
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"Added '{idea}' to the '{category}' list.")

# pick command
@client.tree.command(name="pick", description="Pick a random date idea")
@app_commands.describe(category="Optional: Filter by category (e.g. Food)")
async def pick(interaction: discord.Interaction, category: str = None):
    conn = get_db()
    c = conn.cursor()
    
    if category:
        c.execute("SELECT idea FROM date_ideas WHERE guild_id = %s AND category LIKE %s ORDER BY RANDOM() LIMIT 1", (interaction.guild_id, category))
    else:
        c.execute("SELECT idea FROM date_ideas WHERE guild_id = %s ORDER BY RANDOM() LIMIT 1", (interaction.guild_id,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        await interaction.response.send_message(f"Fate decides: You should do **{row[0]}**.")
    else:
        await interaction.response.send_message("No ideas found.")

# milestone command
@client.tree.command(name="milestone", description="Set a big date (YYYY-MM-DD)")
@app_commands.describe(date="Format: YYYY-MM-DD", name="Name of the event")
async def milestone(interaction: discord.Interaction, date: str, name: str):
    try:
        datetime.strptime(date, '%Y-%m-%d')
        
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO milestones (guild_id, event_name, event_date) VALUES (%s, %s, %s)", 
                  (interaction.guild_id, name, date))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Milestone '{name}' set for {date}.")
    except ValueError:
        await interaction.response.send_message("Invalid date format. Use YYYY-MM-DD (e.g., 2023-12-25).", ephemeral=True)

# days command (countdown)
@client.tree.command(name="days", description="Check days until milestones")
async def days(interaction: discord.Interaction):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT event_name, event_date FROM milestones WHERE guild_id = %s", (interaction.guild_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await interaction.response.send_message("No milestones set yet.")
        return
        
    message = "**Important Dates:**\n"
    today = datetime.now()
    
    for row in rows:
        name, date_str = row
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        delta = target_date - today
        
        if delta.days > 0:
            message += f"• **{name}**: {delta.days} days to go\n"
        else:
            message += f"• **{name}**: {abs(delta.days)} days ago\n"
            
    await interaction.response.send_message(message)

# menu command
@client.tree.command(name="menu", description="Show all available commands")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 UsTwoBot Control Panel",
        description="Here is everything I can do for you two!",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="📸 **Memories**",
        value="`/log [text]` (or attach image) - Save a memory\n`/remember` - View a random memory",
        inline=False
    )

    embed.add_field(
        name="💡 **Date Night**",
        value="`/date [Category] [Idea]` - Add a new idea\n`/pick [Category]` - Randomly choose a date",
        inline=False
    )

    embed.add_field(
        name="❤️ **Fun & Utils**",
        value="`/milestone [YYYY-MM-DD] [Name]` - Set a big date\n`/days` - See countdowns to milestones",
        inline=False
    )

    embed.set_footer(text="Built by Shas")
    
    await interaction.response.send_message(embed=embed)

# --- NEW WEB COMMANDS ---

@client.tree.command(name="view_dates", description="Get a link to see all date ideas in a table")
async def view_dates(interaction: discord.Interaction):
    url = "https://ustwobot.onrender.com/dates"
    await interaction.response.send_message(f"📋 **Here is your full list of date ideas:**\n{url}", ephemeral=True)

@client.tree.command(name="view_memories", description="Get a link to browse your scrapbook")
async def view_memories(interaction: discord.Interaction):
    url = "https://ustwobot.onrender.com/memories"
    await interaction.response.send_message(f"📸 **Here is your digital scrapbook:**\n{url}", ephemeral=True)

keep_alive()
client.run(TOKEN)