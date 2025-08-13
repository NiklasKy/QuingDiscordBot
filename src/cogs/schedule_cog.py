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
        self.announcement_ping_role_id = None
        self.emoji_id = None
        self.emoji_name = None
        self.emoji_animated = None
        
        # Store pending schedule approvals
        # message_id -> (approval_message, formatted_message, original_attachment, context)
        # context: dict with parsed data and UI state (date_range, events, selected_week, mode, editor_user_id)
        self.pending_schedules: Dict[int, Tuple[discord.Message, str, discord.Attachment, dict]] = {}
        
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
            self.announcement_ping_role_id = int(os.getenv("ANNOUNCEMENT_PING_ROLE_ID", "0"))
            self.emoji_id = os.getenv("SCHEDULE_EMOJI_ID", "1234567890123456789")
            self.emoji_name = os.getenv("SCHEDULE_EMOJI_NAME", "cassia_kurukuru")
            self.emoji_animated = os.getenv("SCHEDULE_EMOJI_ANIMATED", "false").lower() == "true"
            
            if self.schedule_channel_id:
                self.schedule_detector = ScheduleDetector(
                    schedule_channel_id=self.schedule_channel_id,
                    emoji_id=self.emoji_id,
                    emoji_name=self.emoji_name,
                    emoji_animated=self.emoji_animated
                )
                logger.info(f"Schedule detector initialized for channel {self.schedule_channel_id}")
                if self.announcement_channel_id:
                    logger.info(f"Announcement channel configured: {self.announcement_channel_id}")
                else:
                    logger.warning("ANNOUNCEMENT_CHANNEL_ID not configured")
                if self.announcement_ping_role_id:
                    logger.info(f"Announcement ping role configured: {self.announcement_ping_role_id}")
                else:
                    logger.info("Announcement ping role not configured (optional)")
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
        
        # If message contains images, process schedule image(s), otherwise maybe handle time edit input
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    await self._process_schedule_image(message, attachment)
            return
        else:
            await self._maybe_handle_time_edit_input(message)
    
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
            
            # Process the image (initially assume current week)
            xml_content = self.schedule_detector.extract_schedule_xml(image)
            if not xml_content:
                logger.error("Failed to extract XML from image")
                return
            parse_current = self.schedule_detector.parse_xml_schedule(xml_content, week_offset=0)
            parse_next = self.schedule_detector.parse_xml_schedule(xml_content, week_offset=1)
            if not parse_current:
                logger.error("Failed to parse XML schedule data (current week)")
                return
            start_date_c, end_date_c, events_c = parse_current
            formatted_current = self.schedule_detector.generate_discord_message((start_date_c, end_date_c), events_c)
            formatted_next = None
            if parse_next:
                start_date_n, end_date_n, events_n = parse_next
                formatted_next = self.schedule_detector.generate_discord_message((start_date_n, end_date_n), events_n)
            
            if formatted_current:
                # Create embed with original image and formatted text
                embed = discord.Embed(
                    title="📅 Schedule Detection Result",
                    description=(
                        "The bot detected a schedule. Choose week via reactions, optionally adjust times, then approve or reject.\n\n"
                        "🗓️ 1️⃣ Current week, 2️⃣ Next week\n"
                        "🕒 Edit times: react, then reply 'index HH:MM' in UTC (e.g. '2 17:00')\n"
                        "✅ Approve, ❌ Reject"
                    ),
                    color=discord.Color.blue()
                )
                
                # Add the formatted schedule text
                embed.add_field(
                    name="Schedule (Current Week)",
                    value=formatted_current,
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
                    value=(
                        "1️⃣ **Current Week** | 2️⃣ **Next Week** | 🕒 **Edit times**\n"
                        "✅ **Approve** (after selection/edits) | ❌ **Reject**"
                    ),
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
                await approval_message.add_reaction("1️⃣")
                await approval_message.add_reaction("2️⃣")
                await approval_message.add_reaction("🕒")
                await approval_message.add_reaction("✅")
                await approval_message.add_reaction("❌")
                
                # Store the pending schedule for later processing
                context = {
                    'xml': xml_content,
                    'current': {
                        'date_range': (start_date_c, end_date_c),
                        'events': events_c,
                        'message': formatted_current,
                    },
                    'next': None,
                    'selected_week': 'current',
                    'mode': 'review',
                    'editor_user_id': None,
                }
                if parse_next:
                    context['next'] = {
                        'date_range': (start_date_n, end_date_n),
                        'events': events_n,
                        'message': formatted_next,
                    }
                self.pending_schedules[approval_message.id] = (approval_message, formatted_current, attachment, context)
                
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
            approval_message, formatted_message, original_attachment, context = self.pending_schedules[payload.message_id]
            
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
            
            # Handle week selection
            if payload.emoji.name == "1️⃣":
                context['selected_week'] = 'current'
                formatted_message = context['current']['message']
                await self._update_approval_embed_message(approval_message, formatted_message, selected_label="Current Week")
                self.pending_schedules[payload.message_id] = (approval_message, formatted_message, original_attachment, context)
            elif payload.emoji.name == "2️⃣" and context.get('next'):
                context['selected_week'] = 'next'
                formatted_message = context['next']['message']
                await self._update_approval_embed_message(approval_message, formatted_message, selected_label="Next Week")
                self.pending_schedules[payload.message_id] = (approval_message, formatted_message, original_attachment, context)
            elif payload.emoji.name == "2️⃣" and not context.get('next'):
                # If next week not available, ignore
                return
            elif payload.emoji.name == "🕒":
                # Enter edit mode for times; only allow one editor at a time
                if context.get('editor_user_id') and context['editor_user_id'] != user.id:
                    try:
                        await approval_message.channel.send(f"Time edit is currently being performed by <@{context['editor_user_id']}>. Please wait.", delete_after=10)
                    except:
                        pass
                    return
                context['mode'] = 'edit_time'
                context['editor_user_id'] = user.id
                helper_text = (
                    "Please reply in this channel with 'index HH:MM' in UTC to change the time.\n"
                    "Example: '2 17:00' to set the second event to 17:00 UTC.\n"
                    "When done, react 🕒 again to exit edit mode."
                )
                try:
                    await approval_message.channel.send(helper_text, delete_after=30)
                except:
                    pass
                # Mark in map
                self.pending_schedules[payload.message_id] = (approval_message, formatted_message, original_attachment, context)
            # Handle approval / rejection
            elif payload.emoji.name == "✅":
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
            
            # Build optional role mention
            content = None
            allowed = discord.AllowedMentions(roles=True, users=False, everyone=False)
            if self.announcement_ping_role_id:
                content = f"<@&{self.announcement_ping_role_id}>"

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
                content=content,
                embed=announcement_embed,
                file=discord.File(io.BytesIO(image_data), filename=f"schedule_announcement.png"),
                allowed_mentions=allowed
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

    async def _update_approval_embed_message(self, approval_message: discord.Message, formatted_message: str, selected_label: str):
        try:
            approval_embed = approval_message.embeds[0]
            # Replace or update the first field (Current/Next Week)
            if approval_embed.fields:
                fields = list(approval_embed.fields)
                # Rebuild embed, but ensure first formatted field reflects selection
                new_embed = discord.Embed(title=approval_embed.title, description=approval_embed.description, color=approval_embed.color)
                # First field is the schedule text field
                new_embed.add_field(name=f"Schedule ({selected_label})", value=formatted_message, inline=fields[0].inline)
                # Copy remaining fields except the original first schedule field
                for f in fields[1:]:
                    new_embed.add_field(name=f.name, value=f.value, inline=f.inline)
                new_embed.set_footer(text=approval_embed.footer.text if approval_embed.footer else discord.Embed.Empty)
                await approval_message.edit(embed=new_embed)
            else:
                # Fallback: just edit description
                new_embed = discord.Embed(title=approval_embed.title, description=formatted_message, color=approval_embed.color)
                new_embed.set_footer(text=approval_embed.footer.text if approval_embed.footer else discord.Embed.Empty)
                await approval_message.edit(embed=new_embed)
        except Exception as e:
            logger.error(f"Failed to update approval embed: {e}")

    @app_commands.command(name="schedule_fix_time", description="Manually correct event time for the pending schedule message")
    async def schedule_fix_time(self, interaction: discord.Interaction, approval_message_id: str, event_index: int, time_hh_mm: str):
        """Fix time of an event (HH:MM, 24h) for the specified pending approval message."""
        # Permission check
        if not self.bot.has_staff_permissions(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        try:
            message_id_int = int(approval_message_id)
        except ValueError:
            await interaction.response.send_message("Invalid approval_message_id.", ephemeral=True)
            return
        if message_id_int not in self.pending_schedules:
            await interaction.response.send_message("No pending schedule found for this message id.", ephemeral=True)
            return
        approval_message, formatted_message, original_attachment, context = self.pending_schedules[message_id_int]
        # Pick selected week's events
        selection = context['selected_week']
        data = context['current'] if selection == 'current' else context.get('next')
        if not data:
            await interaction.response.send_message("Selected week data not available.", ephemeral=True)
            return
        events = data['events']
        if event_index < 1 or event_index > len(events):
            await interaction.response.send_message(f"event_index out of range (1-{len(events)}).", ephemeral=True)
            return
        # Update time and rebuild datetime
        events[event_index - 1]['time'] = time_hh_mm
        self.schedule_detector.rebuild_event_datetime(events[event_index - 1])
        # Regenerate message
        new_formatted = self.schedule_detector.generate_discord_message(data['date_range'], events)
        # Update embed preview
        await self._update_approval_embed_message(approval_message, new_formatted, selected_label=("Current Week" if selection=='current' else "Next Week"))
        # Persist change in context and pending map
        data['message'] = new_formatted
        self.pending_schedules[message_id_int] = (approval_message, new_formatted, original_attachment, context)
        await interaction.response.send_message("Time updated.", ephemeral=True)

    async def _maybe_handle_time_edit_input(self, message: discord.Message):
        """Handle plain text replies for time edits when in edit_time mode.
        Expected format: '<index> <HH:MM>' e.g., '2 17:00'.
        Only staff and the active editor may edit.
        """
        try:
            # Find a pending approval in this channel authored by the bot where mode is edit_time
            for approval_id, (approval_message, formatted_message, original_attachment, context) in list(self.pending_schedules.items()):
                if approval_message.channel.id != message.channel.id:
                    continue
                if context.get('mode') != 'edit_time':
                    continue
                # Only the designated editor can update
                if context.get('editor_user_id') and message.author.id != context['editor_user_id']:
                    continue
                # Permissions check
                if not self.bot.has_staff_permissions(message.author):
                    continue
                # Match input like '2 17:00'
                content = message.content.strip()
                parts = content.split()
                if len(parts) != 2:
                    continue
                idx_str, time_str = parts
                try:
                    idx = int(idx_str)
                except ValueError:
                    continue
                # Update
                selection = context['selected_week']
                data = context['current'] if selection == 'current' else context.get('next')
                if not data:
                    continue
                events = data['events']
                if idx < 1 or idx > len(events):
                    try:
                        await message.channel.send(f"Index out of range (1-{len(events)}).", delete_after=10)
                    except:
                        pass
                    return
                # Set time and rebuild datetime
                events[idx - 1]['time'] = time_str
                self.schedule_detector.rebuild_event_datetime(events[idx - 1])
                # Regenerate message and update embed
                new_formatted = self.schedule_detector.generate_discord_message(data['date_range'], events)
                await self._update_approval_embed_message(approval_message, new_formatted, selected_label=("Current Week" if selection=='current' else "Next Week"))
                data['message'] = new_formatted
                self.pending_schedules[approval_id] = (approval_message, new_formatted, original_attachment, context)
                try:
                    await message.add_reaction("✅")
                except:
                    pass
                return
        except Exception as e:
            logger.error(f"Error handling time edit input: {e}")
    
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