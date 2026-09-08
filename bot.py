import os
import sys
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
from datetime import datetime, time, timezone, timedelta
import aiohttp

# Force stdout and stderr to utf-8 and flush immediately so logs are visible without encoding crashes
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)


# Import our custom modules
import sheets_integration
import gemini_integration

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CHANNEL_ID = os.getenv("DISCORD_MAIN_CHANNEL_ID")

# Setup Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Needed to tag users properly if needed

bot = commands.Bot(command_prefix="!", intents=intents)

# A set to keep track of candidates who have submitted today (for end of day absence check)
submitted_today = set()
has_announced_online = False

async def process_food_photo(message):
    """
    Downloads and analyzes food photo attachments in a message,
    replies with nutrition analysis, updates Google Sheet, and adds confirmation reaction.
    """
    if message.author == bot.user:
        return

    # Check if already processed (has ✅ reaction from bot)
    for reaction in message.reactions:
        if reaction.emoji == "✅":
            users = [u async for u in reaction.users()]
            if bot.user in users:
                print(f"[DEBUG] Message {message.id} already processed. Skipping.")
                return

    if not message.attachments:
        return

    for attachment in message.attachments:
        # Check if it's an image
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
            try:
                await message.add_reaction("⏳") # Processing reaction
            except Exception as re:
                print(f"Reaction error: {re}")
            
            try:
                # Download image bytes
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            mime_type = attachment.content_type or "image/jpeg"
                            
                            # Send to Gemini
                            print(f"[DEBUG] Sending image from {message.author} to Gemini for analysis...")
                            analysis_result = gemini_integration.analyze_food_image(image_bytes, mime_type)
                            print("[DEBUG] Gemini analysis received.")
                            
                            # Reply with analysis (with fallback if message reference fails)
                            try:
                                await message.reply(analysis_result)
                            except Exception as re_err:
                                print(f"Reply reference note: {re_err}, sending directly to channel with mention...")
                                await message.channel.send(f"<@{message.author.id}>\n{analysis_result}")

                            
                            # Update Sheet
                            try:
                                candidates = sheets_integration.get_candidates()
                                candidate_name = message.author.display_name
                                for c in candidates:
                                    if str(c.get('discord_id')) == str(message.author.id):
                                        candidate_name = c.get('name')
                                        break
                                        
                                sheets_integration.mark_attendance(message.author.id, candidate_name, "Present", "Food analyzed")
                            except Exception as se:
                                print(f"Sheets update note: {se}")
                            
                            # Record that they submitted today
                            global submitted_today
                            submitted_today.add(str(message.author.id))
                            
                            try:
                                await message.remove_reaction("⏳", bot.user)
                                await message.add_reaction("✅")
                            except Exception as re2:
                                print(f"Reaction update note: {re2}")
                        else:
                            await message.reply("Sorry, I couldn't download the image.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error processing image: {e}")
                await message.reply("An error occurred while analyzing the image.")


@bot.event
async def on_ready():
    global has_announced_online
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------ Connected Guilds: ------')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
    print('-------------------------------')
    
    if MAIN_CHANNEL_ID:
        try:
            target = bot.get_channel(int(MAIN_CHANNEL_ID))
            if not target:
                print(f'Fetching target channel/thread ID {MAIN_CHANNEL_ID} via API...')
                target = await bot.fetch_channel(int(MAIN_CHANNEL_ID))
            
            print(f'Target channel/thread found: {target.name} (Type: {type(target).__name__})')
            if isinstance(target, discord.Thread):
                print('Target is a Discord Thread. Joining thread...')
                try:
                    await target.join()
                    print('Successfully joined thread!')
                except Exception as je:
                    print(f'Note on thread join: {je}')
            
            # Announce only once per session startup
            if not has_announced_online:
                has_announced_online = True
                print(f'Bot connected to target: {target.name}')
            
            # Scan recent messages (last 20) for any missed food photos while offline
            print('Scanning recent messages for any missed food photos...')
            try:
                async for old_msg in target.history(limit=20):
                    if old_msg.attachments and old_msg.author != bot.user:
                        # Check if message already has ✅ reaction
                        has_check = any(r.emoji == "✅" for r in old_msg.reactions)
                        if not has_check:
                            print(f'Found unanalyzed food photo from {old_msg.author}. Processing now...')
                            await process_food_photo(old_msg)
            except Exception as he:
                print(f'Note on history scan: {he}')

        except Exception as e:
            print(f'Error accessing MAIN_CHANNEL_ID ({MAIN_CHANNEL_ID}): {e}')

    # Start background tasks
    if not daily_roster_check.is_running():
        daily_roster_check.start()
    if not end_of_day_absence_check.is_running():
        end_of_day_absence_check.start()

@tasks.loop(time=time(hour=8, minute=0, tzinfo=timezone(timedelta(hours=5, minutes=30)))) # 8:00 AM IST
async def daily_roster_check():
    """
    Runs daily to remind candidates (Thread creation is disabled as per user request).
    """
    print("Running daily roster reset...")
    global submitted_today
    submitted_today.clear() # Reset for the new day
    
    if not MAIN_CHANNEL_ID:
        return
        
    channel = bot.get_channel(int(MAIN_CHANNEL_ID))
    # You can also fetch it if it's a thread:
    if not channel:
        try:
            channel = await bot.fetch_channel(int(MAIN_CHANNEL_ID))
        except:
            return

    if channel:
        today_str = datetime.now().strftime("%Y-%m-%d")
        await channel.send(f"🌅 Good morning! It's {today_str}. Please post your food photos for today here.")

@tasks.loop(time=time(hour=23, minute=50, tzinfo=timezone(timedelta(hours=5, minutes=30)))) # 11:50 PM IST
async def end_of_day_absence_check():
    """
    Runs at the end of the day to mark absent candidates.
    """
    print("Running end of day absence check...")
    candidates = sheets_integration.get_candidates()
    
    for candidate in candidates:
        discord_id = str(candidate.get('discord_id'))
        name = candidate.get('name')
        
        if discord_id not in submitted_today:
            # Mark absent
            sheets_integration.mark_attendance(discord_id, name, "Absent", "Auto-marked at end of day")
            print(f"Marked {name} as Absent.")

@bot.event
async def on_message(message):
    # Don't respond to ourselves
    if message.author == bot.user:
        return
        
    # Process commands if any
    await bot.process_commands(message)

    # Debug: Log every message the bot sees
    print(f"[DEBUG] Message from {message.author} in channel/thread ID: {message.channel.id} (looking for: {MAIN_CHANNEL_ID})")
    print(f"[DEBUG] Has attachments: {len(message.attachments)}")
    
    # Check if the message is in the designated channel or thread
    target_id = str(MAIN_CHANNEL_ID) if MAIN_CHANNEL_ID else None
    current_channel_id = str(message.channel.id)
    
    parent_id = None
    if isinstance(message.channel, discord.Thread) and message.channel.parent:
        parent_id = str(message.channel.parent.id)
    
    is_target_channel = (current_channel_id == target_id) or (parent_id == target_id)
    
    if target_id and is_target_channel:
        print(f"[DEBUG] Channel matched! Checking for food photos...")
        await process_food_photo(message)




@bot.command(name='absent')
@commands.has_permissions(manage_messages=True) # Require some permissions to use this
async def mark_absent(ctx, member: discord.Member):
    """
    Manually marks a candidate as absent. Usage: !absent @user
    """
    candidates = sheets_integration.get_candidates()
    candidate_name = member.display_name
    for c in candidates:
        if str(c.get('discord_id')) == str(member.id):
            candidate_name = c.get('name')
            break
            
    success = sheets_integration.mark_attendance(member.id, candidate_name, "Absent", "Manually marked by admin")
    if success:
        await ctx.send(f"⚠️ **Status Update:** <@{member.id}> has been marked as Absent for today's food tracking.")
    else:
        await ctx.send(f"Failed to update Google Sheet for <@{member.id}>.")

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN is not set in .env")
    else:
        bot.run(DISCORD_BOT_TOKEN)
