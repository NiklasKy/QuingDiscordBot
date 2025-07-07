"""
Debug Cog

This cog provides debug commands and utilities.
Can be disabled by not loading this cog.
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import logging

logger = logging.getLogger(__name__)

class DebugCog(commands.Cog):
    """Cog for debug commands and utilities."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Debug cog initialized")
    
    @app_commands.command(name="debug", description="Test if the bot is working properly")
    async def debug_command(self, interaction: discord.Interaction):
        """Test command to verify bot functionality."""
        await interaction.response.send_message(
            "✅ Bot is working properly!",
            ephemeral=True
        )
    
    @app_commands.command(name="debug_info", description="Show debug information")
    async def debug_info_command(self, interaction: discord.Interaction):
        """Show debug information about the bot."""
        # Check if user has staff permissions
        if not self.bot.has_staff_permissions(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        info = f"**Bot Debug Info:**\n"
        info += f"• Bot Name: {self.bot.user.name}\n"
        info += f"• Guild Count: {len(self.bot.guilds)}\n"
        info += f"• Latency: {round(self.bot.latency * 1000)}ms\n"
        info += f"• Cogs Loaded: {len(self.bot.cogs)}\n"
        
        await interaction.response.send_message(info, ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(DebugCog(bot)) 