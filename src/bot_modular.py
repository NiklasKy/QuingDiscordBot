"""
Quing Corporation Discord Bot - Modular Version

This bot loads different cogs based on environment variables.
Features can be easily enabled/disabled by setting the appropriate environment variables.
"""

import os
import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuingCorporationBot(commands.Bot):
    """Modular Discord bot for Quing Corporation."""
    
    def __init__(self) -> None:
        """Initialize the bot with required intents."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        # Load environment variables
        load_dotenv()
        
        # Store configuration
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.guild_id = int(os.getenv("DISCORD_GUILD_ID", "0"))
        self.bot_nickname = os.getenv("BOT_NICKNAME")
        
        # Staff roles for permissions
        self.staff_roles = []
        admin_role_id = os.getenv("ADMIN_ROLE_ID")
        mod_role_id = os.getenv("MOD_ROLE_ID")
        
        # Handle admin role(s) - can be comma-separated
        if admin_role_id:
            for role_id in admin_role_id.split(','):
                role_id = role_id.strip()
                if role_id:
                    self.staff_roles.append(int(role_id))
        
        # Handle mod role(s) - can be comma-separated
        if mod_role_id:
            for role_id in mod_role_id.split(','):
                role_id = role_id.strip()
                if role_id:
                    self.staff_roles.append(int(role_id))
        
        # Feature flags
        self.features = {
            'schedule_detection': bool(os.getenv("SCHEDULE_CHANNEL_ID")),
            'whitelist': bool(os.getenv("WHITELIST_CHANNEL_ID")),
            'role_management': bool(os.getenv("WHITELIST_CHANNEL_ID")),  # Same as whitelist for now
            'debug': True  # Always enabled for now
        }
    
    def has_staff_permissions(self, user: discord.User) -> bool:
        """Check if a user has staff permissions."""
        if not hasattr(user, 'roles'):
            return False
        
        # Check if user has any staff role
        user_role_ids = [role.id for role in user.roles]
        return any(role_id in self.staff_roles for role_id in user_role_ids)
    
    async def setup_hook(self):
        """Setup hook called when the bot is starting up."""
        logger.info("Setting up Quing Corporation Bot...")
        
        # Load cogs based on feature flags
        await self._load_cogs()
    
    async def _load_cogs(self):
        """Load cogs based on enabled features."""
        loaded_cogs = []
        
        # Always load schedule detection if configured
        if self.features['schedule_detection']:
            try:
                from .cogs.schedule_cog import ScheduleCog
                await self.add_cog(ScheduleCog(self))
                loaded_cogs.append("Schedule Detection")
                logger.info("✅ Schedule detection cog loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load schedule detection cog: {e}")
        else:
            logger.info("⏭️ Schedule detection disabled (SCHEDULE_CHANNEL_ID not set)")
        
        # Load whitelist cog if enabled
        if self.features['whitelist']:
            try:
                from .cogs.whitelist_cog import WhitelistCog
                await self.add_cog(WhitelistCog(self))
                loaded_cogs.append("Whitelist Management")
                logger.info("✅ Whitelist cog loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load whitelist cog: {e}")
        else:
            logger.info("⏭️ Whitelist management disabled (WHITELIST_CHANNEL_ID not set)")
        
        # Load role management cog if enabled
        if self.features['role_management']:
            try:
                from .cogs.role_cog import RoleCog
                await self.add_cog(RoleCog(self))
                loaded_cogs.append("Role Management")
                logger.info("✅ Role management cog loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load role management cog: {e}")
        else:
            logger.info("⏭️ Role management disabled (WHITELIST_CHANNEL_ID not set)")
        
        # Load debug cog if enabled
        if self.features['debug']:
            try:
                from .cogs.debug_cog import DebugCog
                await self.add_cog(DebugCog(self))
                loaded_cogs.append("Debug Tools")
                logger.info("✅ Debug cog loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load debug cog: {e}")
        else:
            logger.info("⏭️ Debug tools disabled")
        
        logger.info(f"📦 Loaded cogs: {', '.join(loaded_cogs) if loaded_cogs else 'None'}")
    
    async def on_ready(self) -> None:
        """Called when the client is done preparing the data received from Discord."""
        logger.info(f"🤖 Logged in as {self.user}")
        logger.info(f"🌐 Connected to {len(self.guilds)} guilds")
        
        # Try to set nickname if configured
        if self.bot_nickname:
            for guild in self.guilds:
                try:
                    me = guild.me
                    await me.edit(nick=self.bot_nickname)
                    logger.info(f"✅ Nickname changed to '{self.bot_nickname}' in guild: {guild.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to change nickname in guild {guild.name}: {e}")
        
        for guild in self.guilds:
            logger.info(f"   📍 {guild.name} (ID: {guild.id})")
            logger.info(f"      👥 Members: {len(guild.members)}")
            logger.info(f"      🔐 Bot permissions: {guild.me.guild_permissions}")
        
        # Show enabled features
        enabled_features = [name for name, enabled in self.features.items() if enabled]
        logger.info(f"✅ Enabled features: {', '.join(enabled_features) if enabled_features else 'None'}")
        
        logger.info("🚀 Bot is ready!")

async def main() -> None:
    """Main function to run the bot."""
    bot = QuingCorporationBot()
    
    if not bot.discord_token:
        logger.error("❌ DISCORD_TOKEN not set in environment variables")
        return
    
    try:
        await bot.start(bot.discord_token)
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 