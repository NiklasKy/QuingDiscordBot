"""
Schedule Detection Cog

This cog handles automatic detection and formatting of streaming schedules
from images posted in Discord channels.
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import io
from PIL import Image
import logging
from typing import Optional, Dict, Tuple

from ..schedule_detector import ScheduleDetector

logger = logging.getLogger(__name__)

class ScheduleCog(commands.Cog):
    """Cog for handling schedule detection from images."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_detector = None
        self.schedule_channel_id = None
        self.announcement_channel_id = None
        self.emoji_id = None
        
        # Store pending schedule approvals
        self.pending_schedules: Dict[int, Tuple[discord.Message, str, discord.Attachment]] = {}
        
        # Initialize schedule detector when cog is loaded
        self._initialize_detector()
    
    def _initialize_detector(self):
        """Initialize the schedule detector with configuration."""
        try:
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # Get configuration from environment variables
            self.schedule_channel_id = int(os.getenv("SCHEDULE_CHANNEL_ID", "0"))
            self.announcement_channel_id = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0"))
            self.emoji_id = os.getenv("SCHEDULE_EMOJI_ID", "1234567890123456789")
            
            if self.schedule_channel_id:
                self.schedule_detector = ScheduleDetector(
                    schedule_channel_id=self.schedule_channel_id,
                    emoji_id=self.emoji_id
                )
                logger.info(f"Schedule detector initialized for channel {self.schedule_channel_id}")
                if self.announcement_channel_id:
                    logger.info(f"Announcement channel configured: {self.announcement_channel_id}")
                else:
                    logger.warning("ANNOUNCEMENT_CHANNEL_ID not configured")
            else:
                logger.warning("SCHEDULE_CHANNEL_ID not configured, schedule detection disabled")
                
        except Exception as e:
            logger.error(f"Error initializing schedule detector: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle new messages and detect schedule images."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in the schedule channel
        if not self.schedule_detector or message.channel.id != self.schedule_channel_id:
            return
        
        # Check if message contains images
        if not message.attachments:
            return
        
        # Process each image attachment
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                await self._process_schedule_image(message, attachment)
    
    async def _process_schedule_image(self, message: discord.Message, attachment: discord.Attachment):
        """Process a schedule image and post formatted message with approval workflow."""
        try:
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download image: {response.status}")
                        return
                    
                    image_data = await response.read()
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Process the image
            formatted_message = self.schedule_detector.process_schedule_image(image)
            
            if formatted_message:
                # Create embed with original image and formatted text
                embed = discord.Embed(
                    title="📅 Schedule Detection Result",
                    description="The bot has detected and formatted a schedule from your image. Please review and approve or reject.",
                    color=discord.Color.blue()
                )
                
                # Add the formatted schedule text
                embed.add_field(
                    name="Formatted Schedule",
                    value=formatted_message,
                    inline=False
                )
                
                # Add user info
                embed.add_field(
                    name="Submitted by",
                    value=f"{message.author.mention} ({message.author.name})",
                    inline=True
                )
                
                # Add instructions
                embed.add_field(
                    name="Actions",
                    value="✅ **Approve** - Post to announcement channel\n❌ **Reject** - Discard this schedule",
                    inline=False
                )
                
                # Set footer
                embed.set_footer(text="React with ✅ to approve or ❌ to reject")
                
                # Post the embed with the original image
                approval_message = await message.channel.send(
                    embed=embed,
                    file=discord.File(io.BytesIO(image_data), filename=f"schedule_{message.id}.png")
                )
                
                # Add reactions for approval/rejection
                await approval_message.add_reaction("✅")
                await approval_message.add_reaction("❌")
                
                # Store the pending schedule for later processing
                self.pending_schedules[approval_message.id] = (approval_message, formatted_message, attachment)
                
                logger.info(f"Posted approval request for schedule from {message.author.name}")
                
                # Add a reaction to the original message to indicate processing
                try:
                    await message.add_reaction("⏳")
                except:
                    pass
            else:
                # Add a reaction to indicate failure
                try:
                    await message.add_reaction("❌")
                except:
                    pass
                logger.warning(f"Failed to process schedule image from {message.author.name}")
                
        except Exception as e:
            logger.error(f"Error processing schedule image: {e}")
            # Add a reaction to indicate error
            try:
                await message.add_reaction("⚠️")
            except:
                pass
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reactions on schedule approval messages."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is a reaction on a pending schedule
        if payload.message_id in self.pending_schedules:
            await self._handle_schedule_approval(payload)
    
    async def _handle_schedule_approval(self, payload: discord.RawReactionActionEvent):
        """Handle approval/rejection of schedule messages."""
        try:
            # Get the pending schedule data
            approval_message, formatted_message, original_attachment = self.pending_schedules[payload.message_id]
            
            # Get the user who reacted
            guild = self.bot.get_guild(payload.guild_id)
            user = guild.get_member(payload.user_id)
            
            # Check if user has staff permissions
            if not self.bot.has_staff_permissions(user):
                # Remove the reaction if not staff
                try:
                    await approval_message.remove_reaction(payload.emoji, user)
                except:
                    pass
                return
            
            # Handle approval
            if payload.emoji.name == "✅":
                await self._approve_schedule(approval_message, formatted_message, original_attachment, user)
            elif payload.emoji.name == "❌":
                await self._reject_schedule(approval_message, user)
                
        except Exception as e:
            logger.error(f"Error handling schedule approval: {e}")
    
    async def _approve_schedule(self, approval_message: discord.Message, formatted_message: str, 
                               original_attachment: discord.Attachment, approver: discord.Member):
        """Approve a schedule and post it to the announcement channel."""
        try:
            # Get the announcement channel
            announcement_channel = self.bot.get_channel(self.announcement_channel_id)
            if not announcement_channel:
                logger.error(f"Could not find announcement channel with ID {self.announcement_channel_id}")
                return
            
            # Download the original image
            async with aiohttp.ClientSession() as session:
                async with session.get(original_attachment.url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download original image: {response.status}")
                        return
                    
                    image_data = await response.read()
            
            # Post to announcement channel
            announcement_embed = discord.Embed(
                title="📅 Weekly Streaming Schedule",
                description=formatted_message,
                color=discord.Color.green()
            )
            
            # Add approval info
            announcement_embed.set_footer(text=f"Approved by {approver.display_name}")
            
            # Post with image
            await announcement_channel.send(
                embed=announcement_embed,
                file=discord.File(io.BytesIO(image_data), filename=f"schedule_announcement.png")
            )
            
            # Update the approval message
            approval_embed = approval_message.embeds[0]
            approval_embed.color = discord.Color.green()
            approval_embed.add_field(
                name="Status",
                value=f"✅ **Approved** by {approver.mention}\nPosted to <#{self.announcement_channel_id}>",
                inline=False
            )
            
            await approval_message.edit(embed=approval_embed)
            
            # Remove reactions to prevent further interaction
            await approval_message.clear_reactions()
            
            # Remove from pending schedules
            if approval_message.id in self.pending_schedules:
                del self.pending_schedules[approval_message.id]
            
            logger.info(f"Schedule approved by {approver.name} and posted to announcement channel")
            
        except Exception as e:
            logger.error(f"Error approving schedule: {e}")
    
    async def _reject_schedule(self, approval_message: discord.Message, rejector: discord.Member):
        """Reject a schedule and update the message."""
        try:
            # Update the approval message
            approval_embed = approval_message.embeds[0]
            approval_embed.color = discord.Color.red()
            approval_embed.add_field(
                name="Status",
                value=f"❌ **Rejected** by {rejector.mention}\nSchedule discarded",
                inline=False
            )
            
            await approval_message.edit(embed=approval_embed)
            
            # Remove reactions to prevent further interaction
            await approval_message.clear_reactions()
            
            # Remove from pending schedules
            if approval_message.id in self.pending_schedules:
                del self.pending_schedules[approval_message.id]
            
            logger.info(f"Schedule rejected by {rejector.name}")
            
        except Exception as e:
            logger.error(f"Error rejecting schedule: {e}")
    
    @app_commands.command(name="schedule_test", description="Test schedule detection with a URL")
    async def schedule_test(self, interaction: discord.Interaction, image_url: str):
        """Test schedule detection with an image URL."""
        # Check if user has permission
        if not self.bot.has_staff_permissions(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        if not self.schedule_detector:
            await interaction.response.send_message(
                "Schedule detection is not configured. Please set SCHEDULE_CHANNEL_ID in environment variables.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            f"Failed to download image: {response.status}",
                            ephemeral=True
                        )
                        return
                    
                    image_data = await response.read()
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Process the image
            formatted_message = self.schedule_detector.process_schedule_image(image)
            
            if formatted_message:
                await interaction.followup.send(
                    f"**Schedule Detection Test Result:**\n\n{formatted_message}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Failed to detect schedule from the image. Please check the image quality and format.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in schedule test: {e}")
            await interaction.followup.send(
                f"Error processing image: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="schedule_reload", description="Reload schedule detector configuration")
    async def schedule_reload(self, interaction: discord.Interaction):
        """Reload schedule detector configuration."""
        # Check if user has permission
        if not self.bot.has_staff_permissions(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        try:
            self._initialize_detector()
            
            if self.schedule_detector:
                status_msg = f"Schedule detector reloaded successfully. Channel ID: {self.schedule_channel_id}"
                if self.announcement_channel_id:
                    status_msg += f", Announcement Channel ID: {self.announcement_channel_id}"
                else:
                    status_msg += ", Announcement channel not configured"
                
                await interaction.response.send_message(status_msg, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Schedule detector reloaded but not configured. Please check SCHEDULE_CHANNEL_ID.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error reloading schedule detector: {e}")
            await interaction.response.send_message(
                f"Error reloading schedule detector: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(ScheduleCog(bot)) 