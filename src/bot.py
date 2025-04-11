"""
Main Discord bot implementation for QuingCraft.
"""
import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Optional
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
    ERROR_DATABASE
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
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        username = self.username.value.strip()
        
        # Verify Minecraft username
        if not await self.bot.verify_minecraft_username(username):
            await interaction.response.send_message(WHITELIST_INVALID_NAME, ephemeral=True)
            return
        
        # Check for existing pending request
        existing_request = self.bot.db.get_pending_request(interaction.user.id)
        if existing_request:
            await interaction.response.send_message(WHITELIST_PENDING, ephemeral=True)
            return
        
        # Add to database
        if self.bot.db.add_whitelist_request(interaction.user.id, username):
            # Send to mod channel
            mod_channel = self.bot.get_channel(int(os.getenv("MOD_CHANNEL_ID")))
            if mod_channel:
                embed = discord.Embed(
                    title=MOD_REQUEST_TITLE,
                    description=MOD_REQUEST_DESCRIPTION.format(
                        discord_user=interaction.user.mention,
                        minecraft_username=username
                    ),
                    color=discord.Color.orange()
                )
                mod_message = await mod_channel.send(embed=embed)
                await mod_message.add_reaction("✅")
                await mod_message.add_reaction("❌")
                self.bot.pending_requests[interaction.user.id] = mod_message.id
            
            await interaction.response.send_message(WHITELIST_SUCCESS, ephemeral=True)
        else:
            await interaction.response.send_message(ERROR_DATABASE, ephemeral=True)

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
        intents = discord.Intents.default()
        intents.message_content = True
        
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
    
    async def setup_hook(self) -> None:
        """Set up the bot's commands and sync them."""
        
        print("Registering slash commands...")
        
        @self.tree.command(name="qc", description="QuingCraft Verwaltungsbefehle (nur für Staff)")
        @app_commands.describe(
            action="Die Aktion (whitelist)",
            operation="Die Operation (add/remove)",
            username="Minecraft Benutzername"
        )
        @app_commands.choices(
            action=[
                app_commands.Choice(name="whitelist", value="whitelist")
            ],
            operation=[
                app_commands.Choice(name="add", value="add"),
                app_commands.Choice(name="remove", value="remove")
            ]
        )
        async def qc_command(
            interaction: discord.Interaction, 
            action: str,
            operation: str,
            username: str
        ):
            # Check if user has staff role
            if not any(role.id in self.staff_roles for role in interaction.user.roles):
                await interaction.response.send_message("Du hast keine Berechtigung, diesen Befehl zu verwenden.", ephemeral=True)
                return
            
            if action == "whitelist":
                if operation == "add":
                    # Direkt vpw-Befehl verwenden ohne "send" Präfix
                    response = await self.rcon.execute_command(f"vpw add {username}")
                    await interaction.response.send_message(f"Whitelist Befehl ausgeführt:\n```{response}```", ephemeral=True)
                elif operation == "remove":
                    # Direkt vpw-Befehl verwenden ohne "send" Präfix
                    response = await self.rcon.execute_command(f"vpw remove {username}")
                    await interaction.response.send_message(f"Whitelist Befehl ausgeführt:\n```{response}```", ephemeral=True)
        
        # Explizit für die spezifische Guild synchronisieren
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            print(f"Syncing commands to guild ID: {guild_id}")
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Guild command sync complete!")
        
        # Global sync als Backup
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
        
        await self.create_whitelist_message()
        
        # Nachricht über Command-Verfügbarkeit
        print("Commands should now be available in Discord!")
        print(f"Application ID: {self.user.id}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reactions on whitelist requests."""
        if payload.user_id == self.user.id:
            return
        
        if payload.channel_id != int(os.getenv("MOD_CHANNEL_ID")):
            return
        
        message_id = payload.message_id
        user_id = None
        
        # Find the user who made the request
        for req_user_id, req_message_id in self.pending_requests.items():
            if req_message_id == message_id:
                user_id = req_user_id
                break
        
        if not user_id:
            return
        
        emoji = str(payload.emoji)
        if emoji == "✅":
            # Approve the request and add to whitelist
            success, minecraft_username = self.db.approve_request(user_id)
            if success and minecraft_username:
                # Add to the whitelist via RCON
                if await self.rcon.whitelist_add(minecraft_username):
                    # Remove from pending requests
                    if user_id in self.pending_requests:
                        del self.pending_requests[user_id]
                    
                    # Send success message to user
                    user = await self.fetch_user(user_id)
                    if user:
                        await user.send(WHITELIST_APPROVED.format(username=minecraft_username))
                else:
                    print(f"RCON whitelist add failed for {minecraft_username}")
        elif emoji == "❌":
            # Reject the request
            success, minecraft_username = self.db.reject_request(user_id)
            if success:
                # Remove from pending requests
                if user_id in self.pending_requests:
                    del self.pending_requests[user_id]
                
                # Send rejection message to user
                user = await self.fetch_user(user_id)
                if user:
                    await user.send(WHITELIST_REJECTED)

def main() -> None:
    """Start the bot."""
    bot = QuingCraftBot()
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    main() 