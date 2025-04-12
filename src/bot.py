"""
Main Discord bot implementation for QuingCraft.
"""
import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import traceback
import sys
from typing import Optional, Literal, Dict, Any
from dotenv import load_dotenv

from .database import Database
from .rcon import RconHandler
from .texts import (
    WHITELIST_TITLE,
    WHITELIST_DESCRIPTION,
    WHITELIST_INVALID_NAME,
    WHITELIST_PENDING,
    WHITELIST_SUCCESS,
    WHITELIST_APPROVED,
    WHITELIST_REJECTED,
    MOD_REQUEST_TITLE,
    MOD_REQUEST_DESCRIPTION,
    ERROR_DATABASE,
    WHITELIST_DUPLICATE,
    MOD_ERROR_WHITELIST
)

load_dotenv()

class WhitelistModal(discord.ui.Modal, title="Whitelist Request"):
    """Modal for entering Minecraft username."""
    
    username = discord.ui.TextInput(
        label="Minecraft Username",
        placeholder="Enter your Minecraft username...",
        required=True,
        min_length=3,
        max_length=16
    )
    
    reason = discord.ui.TextInput(
        label="Request Notes",
        placeholder="",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Process the submitted modal."""
        try:
            minecraft_username = self.username.value.strip()
            reason = self.reason.value.strip() if self.reason.value else None
            
            user = interaction.user
            print(f"Whitelist request from {user.name} ({user.id}) for username: {minecraft_username}")
            
            # Verify Minecraft username
            if not await self.bot.verify_minecraft_username(minecraft_username):
                await interaction.response.send_message(
                    WHITELIST_INVALID_NAME,
                    ephemeral=True
                )
                return
            
            # Check if the Discord user already has a pending request
            pending_request = self.bot.db.get_pending_request(user.id)
            
            if pending_request:
                print(f"User {user.name} already has a pending request: {pending_request}")
                await interaction.response.send_message(
                    WHITELIST_PENDING,
                    ephemeral=True
                )
                return
            
            # Check if the Minecraft username is already in use
            existing_username_request = self.bot.db.get_request_by_minecraft_username(minecraft_username)
            if existing_username_request and existing_username_request[3] == "pending":
                await interaction.response.send_message(
                    WHITELIST_DUPLICATE,
                    ephemeral=True
                )
                return
            
            # Confirm to the user that the request has been received
            await interaction.response.send_message(
                WHITELIST_SUCCESS,
                ephemeral=True
            )
            
            # Add the request to the database
            added_request = self.bot.db.add_whitelist_request(user.id, minecraft_username, reason)
            if not added_request:
                print(f"Failed to add whitelist request to database for {user.name}")
                await user.send(ERROR_DATABASE)
                return
            
            # Send the request to the moderator channel
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            mod_channel = interaction.client.get_channel(mod_channel_id)
            
            if not mod_channel:
                print(f"Could not find mod channel with ID {mod_channel_id}")
                await user.send(ERROR_GENERIC)
                return
            
            account_created = user.created_at.strftime("%m/%d/%Y")
            joined_server = user.joined_at.strftime("%m/%d/%Y") if user.joined_at else "Unknown"
            
            # Create the embed for moderators
            embed = discord.Embed(
                title=MOD_REQUEST_TITLE,
                description=f"Whitelist request for **{minecraft_username}**\n"
                            f"Discord: <@{user.id}> ({user.name})\n"
                            f"Account created: {account_created}\n"
                            f"Joined server: {joined_server}",
                color=0x3498db
            )

            # Add notes if available
            if reason:
                embed.add_field(name="Notes", value=reason, inline=False)
            
            # Send the embed to the moderator channel
            message = await mod_channel.send(embed=embed)
            
            # Add reactions
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            # Save the message ID for later
            self.bot.pending_requests[user.id] = message.id
            print(f"Added pending request for {user.id}: {message.id}")
        except Exception as e:
            print(f"Error processing whitelist request: {str(e)}")
            traceback.print_exc()
            # Try to send an error message to the user
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        ERROR_PROCESSING,
                        ephemeral=True
                    )
            except:
                pass

class WhitelistView(discord.ui.View):
    """View containing the whitelist button."""
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Request Whitelist", style=discord.ButtonStyle.primary, emoji="🎮")
    async def request_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Handle button click."""
        modal = WhitelistModal(self.bot)
        await interaction.response.send_modal(modal)

class QuingCraftBot(commands.Bot):
    """Main bot class for QuingCraft."""
    
    def __init__(self) -> None:
        """Initialize the bot with necessary components."""
        intents = discord.Intents.all()  # Use all intents
        # intents = discord.Intents.default()
        # intents.message_content = True
        # Make sure we have reaction intents
        # intents.reactions = True
        # intents.guild_messages = True
        # intents.guild_reactions = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
        self.rcon = RconHandler()
        self.pending_requests = {}
        self.whitelist_message_id = None
        
        # Staff role IDs
        self.staff_roles = [
            int(os.getenv("ADMIN_ROLE_ID", "0")),
            int(os.getenv("MOD_ROLE_ID", "0"))
        ]
        
        # Debug message for initialization
        print("DEBUG: Bot initialized with all intents")
    
    async def setup_hook(self) -> None:
        """Set up the bot's commands and sync them."""
        
        print("Registering slash commands...")
        
        # Create a Command Group for /qc
        qc_group = app_commands.Group(name="qc", description="QuingCraft management commands (staff only)")
        
        # Create a Subgroup for /qc whitelist
        whitelist_group = app_commands.Group(name="whitelist", description="Whitelist management commands", parent=qc_group)
        
        @whitelist_group.command(name="add", description="Add a player to the whitelist")
        @app_commands.describe(username="Minecraft Username")
        async def whitelist_add(interaction: discord.Interaction, username: str):
            # Check if user has staff role
            if not any(role.id in self.staff_roles for role in interaction.user.roles):
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
                return
            
            # Use vpw command
            response = await self.rcon.execute_command(f"vpw add {username}")
            await interaction.response.send_message(f"Whitelist command executed:\n```{response}```", ephemeral=True)
        
        @whitelist_group.command(name="remove", description="Remove a player from the whitelist")
        @app_commands.describe(username="Minecraft Username")
        async def whitelist_remove(interaction: discord.Interaction, username: str):
            # Check if user has staff role
            if not any(role.id in self.staff_roles for role in interaction.user.roles):
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
                return
            
            # Use vpw command
            response = await self.rcon.execute_command(f"vpw remove {username}")
            await interaction.response.send_message(f"Whitelist command executed:\n```{response}```", ephemeral=True)
        
        # Add the command groups to the command tree
        self.tree.add_command(qc_group)
        
        # Remove the old qc command if it exists
        for cmd in self.tree.get_commands():
            if cmd.name == "qc" and not isinstance(cmd, app_commands.Group):
                self.tree.remove_command(cmd)
                print("Removed old qc command")
        
        # Sync for the specific guild
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            print(f"Syncing commands to guild ID: {guild_id}")
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Guild command sync complete!")
        
        # Global sync as backup
        print("Starting global command sync...")
        await self.tree.sync()
        print("Global command sync complete!")
    
    async def create_whitelist_message(self) -> None:
        """Create or update the whitelist message in the channel."""
        channel_id = int(os.getenv("WHITELIST_CHANNEL_ID"))
        channel = self.get_channel(channel_id)
        
        if not channel:
            print(f"Could not find channel with ID {channel_id}")
            return
        
        # Delete old message if it exists
        if self.whitelist_message_id:
            try:
                old_message = await channel.fetch_message(self.whitelist_message_id)
                await old_message.delete()
            except discord.NotFound:
                pass
        
        # Create new message
        embed = discord.Embed(
            title=WHITELIST_TITLE,
            description=WHITELIST_DESCRIPTION,
            color=discord.Color.blue()
        )
        
        view = WhitelistView(self)
        message = await channel.send(embed=embed, view=view)
        self.whitelist_message_id = message.id
        print(f"Created whitelist message with ID {message.id}")
    
    async def verify_minecraft_username(self, username: str) -> bool:
        """Verify if a Minecraft username is valid using Mojang API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as response:
                return response.status == 200
    
    async def on_ready(self) -> None:
        """Handle bot ready event."""
        print(f"Logged in as {self.user.name} ({self.user.id})")
        print(f"Bot is a member of {len(self.guilds)} guilds")
        
        for guild in self.guilds:
            print(f" - {guild.name} (ID: {guild.id})")
        
        # Loading pending requests from the database
        print("Loading pending requests from database...")
        await self.load_pending_requests()
        
        await self.create_whitelist_message()
        
        # Nachricht über Command-Verfügbarkeit
        print("Commands should now be available in Discord!")
        print(f"Application ID: {self.user.id}")
        
        # Debug: Liste alle Event-Listener auf
        print("\nDEBUG: Registered event listeners:")
        for listener in self._listeners:
            print(f" - {listener}")
    
    async def load_pending_requests(self) -> None:
        """Load pending requests from the database."""
        try:
            # Hole alle ausstehenden Anfragen aus der Datenbank und versuche, die Nachrichten zu finden
            pending_requests = self.db.get_all_pending_requests()
            if not pending_requests:
                print("No pending requests found in database")
                return
            
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            mod_channel = self.get_channel(mod_channel_id)
            if not mod_channel:
                print(f"Could not find mod channel with ID {mod_channel_id}")
                return
            
            print(f"Found {len(pending_requests)} pending requests in database")
            
            # Durchsuche die letzten 100 Nachrichten im Mod-Kanal
            async for message in mod_channel.history(limit=100):
                if not message.embeds:
                    continue
                
                # Prüfe, ob die Nachricht eine Whitelist-Anfrage ist
                embed = message.embeds[0]
                if embed.title != MOD_REQUEST_TITLE:
                    continue
                
                # Extrahiere die Benutzer-ID aus dem Embed
                import re
                match = re.search(r"<@(\d+)>", embed.description)
                if not match:
                    continue
                
                user_id = int(match.group(1))
                
                # Prüfe, ob dieser Benutzer eine ausstehende Anfrage hat
                for req in pending_requests:
                    if req[1] == user_id:  # req[1] sollte die discord_id sein
                        print(f"Found message {message.id} for pending request from user {user_id}")
                        self.pending_requests[user_id] = message.id
                        break
            
            print(f"Loaded {len(self.pending_requests)} pending requests into memory")
        except Exception as e:
            print(f"Error loading pending requests: {e}")
            traceback.print_exc()
    
    # Nur ein Event-Listener für on_message behalten
    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages and commands."""
        if message.author.bot:
            return
        
        # Debug-Befehle
        if message.content.startswith("!debug"):
            if message.content == "!debug-requests":
                await self._debug_requests(message)
            elif message.content.startswith("!debug-reactions"):
                await self._debug_reactions(message)
            elif message.content.startswith("!debug-add"):
                parts = message.content.split()
                if len(parts) > 1:
                    username = parts[1]
                    await message.channel.send(f"Force adding {username} to whitelist...")
                    result = await self.rcon.whitelist_add(username)
                    await message.channel.send(f"Result: {'Success' if result else 'Failed'}")
                else:
                    await message.channel.send("Please provide a username")
            elif message.content.startswith("!debug-memory"):
                # Zeige wichtige Variablen und ihren Inhalt
                memory_info = "**Memory Debug:**\n"
                memory_info += f"- pending_requests: {self.pending_requests}\n"
                memory_info += f"- whitelist_message_id: {self.whitelist_message_id}\n"
                memory_info += f"- staff_roles: {self.staff_roles}\n"
                await message.channel.send(memory_info)
        
        # Normal message processing
        await self.process_commands(message)
    
    async def _debug_requests(self, message):
        """Handle debug-requests command."""
        if not self.pending_requests:
            await message.channel.send("No pending requests in memory.")
            return
        
        requests_info = "**Current pending requests:**\n"
        for user_id, msg_id in self.pending_requests.items():
            # Versuche, weitere Informationen über die Anfrage zu bekommen
            request = self.db.get_pending_request(user_id)
            minecraft_name = request[2] if request else "Unknown"
            requests_info += f"• User {user_id} ({minecraft_name}): Message {msg_id}\n"
        
        await message.channel.send(requests_info)
    
    async def _debug_reactions(self, message):
        """Handle debug-reactions command."""
        parts = message.content.split()
        if len(parts) <= 1:
            await message.channel.send("Please provide a message ID to check")
            return
        
        try:
            message_id = int(parts[1])
            await message.channel.send(f"Checking reactions on message {message_id}...")
            await self.check_reactions(message_id)
        except ValueError:
            await message.channel.send("Invalid message ID. Please provide a valid number.")
    
    # Eventlistener für Reaktionen verbessern
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reactions on whitelist requests using raw events."""
        # Ignoriere Bot-eigene Reaktionen
        if payload.user_id == self.user.id:
            print(f"[REACTION] Ignoring bot's own reaction")
            return
        
        # Ignoriere Reaktionen außerhalb des Mod-Channels
        mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
        if payload.channel_id != mod_channel_id:
            return
        
        emoji = str(payload.emoji)
        message_id = payload.message_id
        moderator_id = payload.user_id  # ID des Moderators, der reagiert hat
        
        print(f"[REACTION] Detected: {emoji} on message {message_id} by user {moderator_id}")
        
        # Besonders wichtig: Prüfe, ob dieses message_id in pending_requests als Wert existiert
        found_user_id = None
        for user_id, req_message_id in self.pending_requests.items():
            if req_message_id == message_id:
                found_user_id = user_id
                print(f"[REACTION] Found matching request from user {found_user_id}")
                break
        
        if found_user_id is None:
            print(f"[REACTION] No matching request found for message {message_id}")
            
            # Versuche trotzdem, die Nachricht zu finden und die User-ID zu extrahieren
            try:
                channel = self.get_channel(payload.channel_id)
                if not channel:
                    print(f"[REACTION] Could not get channel {payload.channel_id}")
                    return
                
                message = await channel.fetch_message(message_id)
                if not message or not message.embeds:
                    print(f"[REACTION] Message has no embeds")
                    return
                
                embed = message.embeds[0]
                # Überprüfe, ob es sich um eine Whitelist-Anfrage handelt
                if embed.title != MOD_REQUEST_TITLE:
                    print(f"[REACTION] Message is not a whitelist request")
                    return
                
                desc = embed.description
                
                import re
                match = re.search(r"<@(\d+)>", desc)
                if match:
                    found_user_id = int(match.group(1))
                    print(f"[REACTION] Extracted user ID from embed: {found_user_id}")
                    
                    # Speichere für die Zukunft
                    self.pending_requests[found_user_id] = message_id
                else:
                    print(f"[REACTION] Could not extract user ID from embed")
                    return
            except Exception as e:
                print(f"[REACTION] Error extracting user ID: {e}")
                traceback.print_exc()
                return
        
        # Verarbeite die Reaktion basierend auf dem Emoji
        if emoji == "✅":
            print(f"[REACTION] Processing approval for user {found_user_id} by moderator {moderator_id}")
            await self._approve_whitelist_request_with_mod(found_user_id, payload.channel_id, moderator_id)
        elif emoji == "❌":
            print(f"[REACTION] Processing rejection for user {found_user_id} by moderator {moderator_id}")
            await self._reject_whitelist_request_with_mod(found_user_id, moderator_id)
    
    async def _approve_whitelist_request_with_mod(self, user_id: int, channel_id: int, moderator_id: int) -> None:
        """Approve a whitelist request with moderator ID."""
        try:
            # Hole die Anfrage aus der Datenbank
            request = self.db.get_pending_request(user_id)
            if not request:
                print(f"DEBUG: No pending request found for user {user_id}")
                return
            
            request_id = request[0]
            minecraft_username = request[2]
            print(f"DEBUG: Processing whitelist approval for {minecraft_username} by moderator {moderator_id}")
            
            # Versuche, den Spieler zur Whitelist hinzuzufügen
            print(f"DEBUG: Adding {minecraft_username} to whitelist")
            success = await self.rcon.whitelist_add(minecraft_username)
            
            if success:
                print(f"DEBUG: Successfully added {minecraft_username} to whitelist")
                
                # Aktualisiere den Anfragestatus mit der Moderator-ID
                db_success = self.db.update_request_status(request_id, "approved", moderator_id)
                print(f"DEBUG: Database update result: {db_success}")
                
                # Entferne aus den ausstehenden Anfragen
                if user_id in self.pending_requests:
                    del self.pending_requests[user_id]
                
                # Benachrichtige den Benutzer
                try:
                    discord_user = await self.fetch_user(user_id)
                    if discord_user:
                        await discord_user.send(WHITELIST_APPROVED.format(username=minecraft_username))
                        print(f"DEBUG: Sent approval message to user {user_id}")
                except Exception as e:
                    print(f"DEBUG: Error sending message to user: {str(e)}")
            else:
                print(f"DEBUG: Failed to add {minecraft_username} to whitelist")
                
                # Benachrichtige den Moderator über das Problem
                try:
                    channel = self.get_channel(channel_id)
                    if channel:
                        await channel.send(MOD_ERROR_WHITELIST.format(username=minecraft_username), delete_after=60)
                except Exception as e:
                    print(f"DEBUG: Error sending error message: {str(e)}")
        except Exception as e:
            print(f"DEBUG: Error in _approve_whitelist_request_with_mod: {str(e)}")
            traceback.print_exc()
    
    async def _reject_whitelist_request_with_mod(self, user_id: int, moderator_id: int) -> None:
        """Reject a whitelist request with moderator ID."""
        try:
            # Hole die Anfrage aus der Datenbank
            request = self.db.get_pending_request(user_id)
            if not request:
                print(f"DEBUG: No pending request found for user {user_id}")
                return
            
            request_id = request[0]
            minecraft_username = request[2]
            print(f"DEBUG: Processing whitelist rejection for {minecraft_username} by moderator {moderator_id}")
            
            # Aktualisiere den Anfragestatus mit der Moderator-ID
            db_success = self.db.update_request_status(request_id, "rejected", moderator_id)
            print(f"DEBUG: Database update result: {db_success}")
            
            # Entferne aus den ausstehenden Anfragen
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]
            
            # Benachrichtige den Benutzer
            try:
                discord_user = await self.fetch_user(user_id)
                if discord_user:
                    await discord_user.send(WHITELIST_REJECTED)
                    print(f"DEBUG: Sent rejection message to user {user_id}")
            except Exception as e:
                print(f"DEBUG: Error sending message to user: {str(e)}")
        except Exception as e:
            print(f"DEBUG: Error in _reject_whitelist_request_with_mod: {str(e)}")
            traceback.print_exc()

    # Direkte Debug-Commands
    
    @commands.command(name="debug_requests")
    async def debug_requests_command(self, ctx):
        """List all pending whitelist requests."""
        requests_info = "Current pending requests:\n"
        for user_id, msg_id in self.pending_requests.items():
            requests_info += f"• User {user_id}: Message {msg_id}\n"
        
        await ctx.send(requests_info if self.pending_requests else "No pending requests.")
    
    @commands.command(name="debug_reactions")
    async def debug_reactions_command(self, ctx, message_id: int = None):
        """Check reactions on a message."""
        if not message_id:
            await ctx.send("Please provide a message ID to check.")
            return
        
        await ctx.send(f"Checking reactions on message {message_id}...")
        await self.check_reactions(message_id)
    
    @commands.command(name="whitelist_force_add")
    async def whitelist_force_add_command(self, ctx, username: str = None):
        """Force add a user to the whitelist."""
        if not username:
            await ctx.send("Please provide a Minecraft username.")
            return
        
        await ctx.send(f"Attempting to add {username} to whitelist...")
        result = await self.rcon.whitelist_add(username)
        await ctx.send(f"Result: {'Success' if result else 'Failed'}")
    
    @commands.command(name="whitelist_check")
    async def whitelist_check_command(self, ctx, username: str = None):
        """Check if a user is on the whitelist."""
        if not username:
            await ctx.send("Please provide a Minecraft username.")
            return
        
        await ctx.send(f"Checking if {username} is on the whitelist...")
        result = await self.rcon.whitelist_check(username)
        await ctx.send(f"Result: {username} is {'on' if result else 'not on'} the whitelist.")

def main() -> None:
    """Start the bot."""
    bot = QuingCraftBot()
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    main() 