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
import datetime
import re

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
    MOD_ERROR_WHITELIST,
    ERROR_PROCESSING,
    ERROR_PERMISSION_DENIED,
    ERROR_GENERIC,
    WHITELIST_COMMAND_SUCCESS,
    WHITELIST_ADD_SUCCESS,
    WHITELIST_REMOVE_SUCCESS,
    WHITELIST_CHECK_RESULT,
    WHITELIST_CHECK_ON,
    WHITELIST_CHECK_OFF,
    DEBUG_PROVIDE_USERNAME,
    DEBUG_ATTEMPT_ADD,
    DEBUG_RESULT,
    DEBUG_PROVIDE_MESSAGE_ID,
    DEBUG_CHECKING_REACTIONS,
    DEBUG_CHECKING_WHITELIST,
    DEBUG_NO_PENDING_REQUESTS,
    DEBUG_INVALID_MESSAGE_ID,
    # New role-related text constants
    ROLE_REQUEST_TITLE,
    ROLE_REQUEST_DESCRIPTION,
    ROLE_REQUEST_INVALID_NAME,
    ROLE_REQUEST_SUCCESS,
    ROLE_REQUEST_APPROVED,
    ROLE_REQUEST_REJECTED,
    ROLE_ERROR_APPROVAL,
    ROLE_ERROR_REJECTION,
    ROLE_SUB_ERROR,
    ROLE_NO_SUB,
    ROLE_SELECTOR_TITLE,
    ROLE_SELECTOR_DESCRIPTION,
    ROLE_SELECTOR_SUB_TITLE,
    ROLE_SELECTOR_SUB_DESCRIPTION,
    ROLE_SELECTOR_REQUEST_TITLE,
    ROLE_SELECTOR_REQUEST_DESCRIPTION
)

load_dotenv()

class RoleModal(discord.ui.Modal, title="Role Request"):
    """Modal for updating Minecraft roles."""
    
    minecraft_username = discord.ui.TextInput(
        label="Minecraft Username",
        placeholder="Enter your Minecraft username...",
        required=True,
        min_length=3,
        max_length=16
    )
    
    twitch_username = discord.ui.TextInput(
        label="Twitch Username",
        placeholder="Enter your Twitch username (optional)",
        required=False,
        min_length=2,
        max_length=25
    )
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Process the submitted role request."""
        try:
            minecraft_username = self.minecraft_username.value.strip()
            twitch_username = self.twitch_username.value.strip() if self.twitch_username.value else None
            
            user = interaction.user
            print(f"Role update request from {user.name} ({user.id}) for username: {minecraft_username}")
            
            # Verify Minecraft username
            if not await self.bot.verify_minecraft_username(minecraft_username):
                await interaction.response.send_message(
                    "Invalid Minecraft username. Please provide a valid username.",
                    ephemeral=True
                )
                return
            
            # Acknowledge receipt first
            await interaction.response.send_message(
                "Your role update request has been received. Processing...",
                ephemeral=True
            )
            
            # Process role update based on user's Discord roles
            roles_updated = await self.bot.update_minecraft_roles(user, minecraft_username, twitch_username)
            
            # Notify the user of the result
            if roles_updated:
                # Send a followup message to confirm success
                try:
                    await interaction.followup.send(
                        f"Your in-game roles have been updated successfully!",
                        ephemeral=True
                    )
                except:
                    await user.send(f"Your in-game roles have been updated successfully!")
            else:
                # Send a followup message about failure
                try:
                    await interaction.followup.send(
                        "Failed to update your in-game roles. Please contact a staff member for assistance.",
                        ephemeral=True
                    )
                except:
                    await user.send("Failed to update your in-game roles. Please contact a staff member for assistance.")
                    
        except Exception as e:
            print(f"Error processing role request: {str(e)}")
            traceback.print_exc()
            # Try to send an error message to the user
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        ERROR_PROCESSING,
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        ERROR_PROCESSING,
                        ephemeral=True
                    )
            except:
                pass

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
                description=MOD_REQUEST_DESCRIPTION.format(
                    minecraft_username=minecraft_username,
                    discord_user=f"<@{user.id}> ({user.name})",
                    account_created=account_created,
                    joined_server=joined_server
                ),
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
            
            # Add the request to the database - now with message_id
            added_request = self.bot.db.add_whitelist_request(user.id, minecraft_username, reason, message.id)
            if not added_request:
                print(f"Failed to add whitelist request to database for {user.name}")
                await user.send(ERROR_DATABASE)
                return
            
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

class RoleRequestModal(discord.ui.Modal, title="Request Special Role"):
    """Modal for requesting a special role."""
    
    minecraft_username = discord.ui.TextInput(
        label="Minecraft Username",
        placeholder="Enter your Minecraft username...",
        required=True,
        min_length=3,
        max_length=16
    )
    
    requested_role = discord.ui.TextInput(
        label="Requested Role",
        placeholder="Enter either 'VIP' or 'VTuber'",
        required=True,
        min_length=2,
        max_length=20
    )
    
    reason = discord.ui.TextInput(
        label="Reason for Request",
        placeholder="Why should you receive this role? Provide details to support your request.",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Process the submitted role request."""
        try:
            minecraft_username = self.minecraft_username.value.strip()
            requested_role = self.requested_role.value.strip()
            reason = self.reason.value.strip()
            
            user = interaction.user
            print(f"Role request from {user.name} ({user.id}) for role: {requested_role}, username: {minecraft_username}")
            
            # Verify Minecraft username
            if not await self.bot.verify_minecraft_username(minecraft_username):
                await interaction.response.send_message(
                    ROLE_REQUEST_INVALID_NAME,
                    ephemeral=True
                )
                return
            
            # Validate role name
            allowed_roles = ["default", "sub", "vip", "VTuber"]
            if requested_role not in allowed_roles:
                await interaction.response.send_message(
                    f"Ungültige Rolle: **{requested_role}**. Erlaubte Rollen sind: {', '.join(allowed_roles)}",
                    ephemeral=True
                )
                return
            
            # Confirm to the user that the request has been received
            await interaction.response.send_message(
                ROLE_REQUEST_SUCCESS.format(role=requested_role),
                ephemeral=True
            )
            
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
                title=ROLE_REQUEST_TITLE,
                description=f"**Minecraft Username**: {minecraft_username}\n**Requested Role**: {requested_role}\n**Discord**: <@{user.id}> ({user.name})\n**Account Created**: {account_created}\n**Joined Server**: {joined_server}",
                color=0x9b59b6
            )
            
            # Add reason
            embed.add_field(name="Reason", value=reason, inline=False)
            
            # Send the embed to the moderator channel
            message = await mod_channel.send(embed=embed)
            
            # Add reactions for approval/rejection
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            # Add role request to database
            self.bot.db.add_role_request(user.id, minecraft_username, requested_role, reason, message.id)
            
            # Store the role request in memory
            if not hasattr(self.bot, 'role_requests'):
                self.bot.role_requests = {}
            
            # Format: {user_id: (message_id, minecraft_username, requested_role)}
            self.bot.role_requests[user.id] = (message.id, minecraft_username, requested_role)
            print(f"Added role request for {user.id}: {message.id}, {requested_role}")
            
        except Exception as e:
            print(f"Error processing role request: {str(e)}")
            traceback.print_exc()
            # Try to send an error message to the user
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        ERROR_PROCESSING,
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        ERROR_PROCESSING,
                        ephemeral=True
                    )
            except:
                pass

class RoleSelectorView(discord.ui.View):
    """View containing role selection buttons."""
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Get Sub Role", style=discord.ButtonStyle.success, emoji="⭐", custom_id="role_selector:sub_v2")
    async def get_sub_role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Handle Sub role button click."""
        user = interaction.user
        
        # Check if user has the Sub role on Discord
        sub_role_id = None
        for key, value in os.environ.items():
            if key.startswith("ROLE_MAPPING_SUB"):
                parts = value.split(":", 1)
                if len(parts) == 2:
                    discord_role_ids_str = parts[0]
                    discord_role_ids = [int(role_id.strip()) for role_id in discord_role_ids_str.split(",")]
                    if discord_role_ids:
                        sub_role_id = discord_role_ids[0]
                        break
        
        if not sub_role_id:
            await interaction.response.send_message(
                ROLE_SUB_ERROR,
                ephemeral=True
            )
            return
        
        # Check if user has the Discord Sub role
        has_sub_role = False
        for role in user.roles:
            if role.id == sub_role_id:
                has_sub_role = True
                break
        
        if not has_sub_role:
            await interaction.response.send_message(
                ROLE_NO_SUB,
                ephemeral=True
            )
            return
        
        # Ask for Minecraft username
        modal = RoleModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Request Special Role", style=discord.ButtonStyle.primary, emoji="🏆", custom_id="role_selector:request_v2")
    async def request_special_role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Handle special role request button click."""
        modal = RoleRequestModal(self.bot)
        await interaction.response.send_modal(modal)

class AdminCommands(commands.Cog):
    """Admin commands for the QuingCraft server."""
    
    def __init__(self, bot):
        self.bot = bot
        # Create the command group structure
        self.qc_group = app_commands.Group(name="qc", description="QuingCraft management commands (staff only)")
        self.whitelist_group = app_commands.Group(name="whitelist", description="Whitelist management commands", parent=self.qc_group)
        self.roles_group = app_commands.Group(name="roles", description="Role management commands", parent=self.qc_group)
        
        # Register the whitelist commands
        # Using the simpler method to register commands with parameters
        self.whitelist_group.add_command(app_commands.Command(
            name="add",
            description="Add a player to the whitelist and link to a Discord user",
            callback=self.whitelist_add,
            extras={"requires_staff": True}
        ))
        
        self.whitelist_group.add_command(app_commands.Command(
            name="remove",
            description="Remove a player from the whitelist",
            callback=self.whitelist_remove,
            extras={"requires_staff": True}
        ))
        
        self.whitelist_group.add_command(app_commands.Command(
            name="show",
            description="Show all players on the whitelist",
            callback=self.whitelist_show,
            extras={"requires_staff": True}
        ))
        
        # Register the role commands
        self.roles_group.add_command(app_commands.Command(
            name="update",
            description="Update a player's roles based on their Discord roles",
            callback=self.roles_update,
            extras={"requires_staff": True}
        ))
        
        self.roles_group.add_command(app_commands.Command(
            name="check",
            description="Check a user's current Discord roles and mapped Minecraft roles",
            callback=self.roles_check,
            extras={"requires_staff": True}
        ))
        
        # Add direct role command to qc group
        self.qc_group.add_command(app_commands.Command(
            name="role",
            description="Set a specific role for a Minecraft player",
            callback=self.role_set,
            extras={"requires_staff": True}
        ))
        
        # Add the groups to the bot
        bot.tree.add_command(self.qc_group)
    
    async def whitelist_add(self, interaction: discord.Interaction, username: str, discord_user: Optional[discord.Member] = None):
        """Add a player to the whitelist."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Acknowledge the command received before long-running operations
        await interaction.response.defer(ephemeral=False)
        
        # Get the target Discord user ID
        target_discord_id = None
        if discord_user:
            target_discord_id = discord_user.id
            target_user_mention = discord_user.mention
        else:
            # If no Discord user provided, use the command issuer
            target_discord_id = interaction.user.id
            target_user_mention = interaction.user.mention
        
        # Use the more robust whitelist_add method from the RCON handler
        result = await self.bot.rcon.whitelist_add(username)
        
        if result:
            # If successfully added to whitelist, add an entry to the database
            try:
                # Create a whitelist entry in the database with approved status
                entry_added = self.bot.db.add_whitelist_request(
                    discord_id=target_discord_id,
                    minecraft_username=username,
                    reason=f"Manually added by {interaction.user.name}",
                    message_id=None
                )
                
                # Update the status to approved
                # Get the request ID from newly added request
                request = self.bot.db.get_pending_request(target_discord_id)
                if request:
                    request_id = request[0]
                    self.bot.db.update_request_status(
                        request_id=request_id,
                        status="approved",
                        moderator_id=interaction.user.id
                    )
                    print(f"Added database entry for {username} linked to Discord ID {target_discord_id}")
                
                # Add the whitelist role to the target user
                await self.bot.add_whitelist_role(target_discord_id)
                print(f"Added whitelist role to user with Discord ID {target_discord_id} for Minecraft username {username}")
            except Exception as e:
                print(f"Error adding database entry or whitelist role: {str(e)}")
                traceback.print_exc()
        
        # Send the result back to the user - public for everyone to see
        if result:
            await interaction.followup.send(
                f"{WHITELIST_ADD_SUCCESS.format(username=username)}\nWhitelisted account linked to {target_user_mention}."
            )
        else:
            await interaction.followup.send(f"Failed to add {username} to the whitelist. Check the logs for details.")
    
    async def whitelist_remove(self, interaction: discord.Interaction, username: str):
        """Remove a player from the whitelist."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Acknowledge the command received before long-running operations
        await interaction.response.defer(ephemeral=False)
        
        # Before removing from whitelist, try to find the Discord user by the Minecraft username
        # to remove their role
        user_entry = None
        try:
            # Get all whitelist entries and find one with matching username
            whitelist_users = self.bot.db.get_whitelist_users()
            for mc_username, discord_id in whitelist_users:
                if mc_username.lower() == username.lower():
                    user_entry = (mc_username, discord_id)
                    break
            
            # If found, remove the whitelist role
            if user_entry:
                discord_id = user_entry[1]
                await self.bot.remove_whitelist_role(discord_id)
                print(f"Removed whitelist role from user with Discord ID {discord_id} for Minecraft username {username}")
        except Exception as e:
            print(f"Error removing whitelist role: {str(e)}")
            traceback.print_exc()
        
        # Use the more robust whitelist_remove method from the RCON handler
        result = await self.bot.rcon.whitelist_remove(username)
        
        # Send the result back to the user - public for everyone to see
        if result:
            await interaction.followup.send(WHITELIST_REMOVE_SUCCESS.format(username=username))
        else:
            await interaction.followup.send(f"Failed to remove {username} from the whitelist. Check the logs for details.")
    
    async def whitelist_show(self, interaction: discord.Interaction):
        """Show all players on the whitelist."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Acknowledge the command received before long-running operations
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Get the whitelist directly via RCON
            rcon_response = await self.bot.rcon.execute_command("vpw list")
            print(f"Raw VPW list response: {rcon_response}")
            
            # Get user mappings from database
            whitelist_users = self.bot.db.get_whitelist_users()
            user_mappings = {mc_username.lower(): discord_id for mc_username, discord_id in whitelist_users}
            
            # Format and send the response
            if rcon_response and "Error:" not in rcon_response:
                # Process the response to extract usernames
                usernames = []
                
                # Debug the raw response format
                lines = rcon_response.strip().split('\n')
                print(f"Split lines from response: {lines}")
                
                # Parse the usernames from the response - handle different formats
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    print(f"Processing line: '{line}'")
                    # Check for common patterns
                    if "Whitelisted" in line or "Players:" in line:
                        # Skip header lines
                        continue
                    
                    # Extract actual username - could be various formats
                    # Try to handle common formats:
                    # 1. Just the username
                    # 2. Username with prefix/suffix
                    # 3. Username in a list format
                    
                    # Replace any special chars or prefixes that might be in the username display
                    username = line.strip()
                    username = username.replace('•', '').strip()
                    username = username.replace('-', '').strip()
                    username = username.replace('*', '').strip()
                    
                    # If we have a player username that contains meaningful characters, add it
                    if username and len(username) >= 3 and username != "Whitelisted":
                        usernames.append(username)
                        print(f"Added username: '{username}'")
                
                # If no usernames were extracted, try a more aggressive approach
                if not usernames:
                    print("No usernames extracted with normal parsing, trying alternative method")
                    # Join all text and try to extract usernames
                    all_text = ' '.join(lines)
                    words = all_text.split()
                    for word in words:
                        word = word.strip()
                        # Remove special characters
                        word = ''.join(c for c in word if c.isalnum() or c == '_')
                        if word and len(word) >= 3 and word != "Whitelisted" and word != "Players":
                            usernames.append(word)
                            print(f"Added username with alternative method: '{word}'")
                
                # Create a detailed embed with user mappings
                embed = discord.Embed(
                    title="Minecraft Whitelist",
                    description=f"Total whitelisted players: {len(usernames)}",
                    color=discord.Color.green()
                )
                
                # Add original response for debugging in case parsing fails
                embed.add_field(
                    name="Debug: Original Response",
                    value=f"```{rcon_response[:1000]}```",
                    inline=False
                )
                
                # Sort usernames alphabetically
                usernames.sort()
                
                # Group usernames with discord mapping in one field and without in another
                mapped_users = []
                unmapped_users = []
                
                for username in usernames:
                    lower_username = username.lower()
                    if lower_username in user_mappings:
                        discord_id = user_mappings[lower_username]
                        mapped_users.append(f"• {username} - <@{discord_id}>")
                    else:
                        unmapped_users.append(f"• {username}")
                
                # Add mapped users to embed
                if mapped_users:
                    embed.add_field(
                        name="Players with Discord mapping",
                        value="\n".join(mapped_users[:25]),  # Discord embed field limit
                        inline=False
                    )
                    
                    # Add additional fields if more than 25 users
                    if len(mapped_users) > 25:
                        chunks = [mapped_users[i:i+25] for i in range(25, len(mapped_users), 25)]
                        for i, chunk in enumerate(chunks):
                            embed.add_field(
                                name=f"Players with Discord mapping (continued {i+1})",
                                value="\n".join(chunk),
                                inline=False
                            )
                
                # Add unmapped users to embed
                if unmapped_users:
                    # Split into chunks of 25 for embed field limits
                    chunks = [unmapped_users[i:i+25] for i in range(0, len(unmapped_users), 25)]
                    for i, chunk in enumerate(chunks):
                        field_name = "Players without Discord mapping"
                        if i > 0:
                            field_name += f" (continued {i+1})"
                        embed.add_field(
                            name=field_name,
                            value="\n".join(chunk),
                            inline=False
                        )
                
                # Send the embed
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"Failed to retrieve whitelist: {rcon_response}")
        except Exception as e:
            print(f"Error in whitelist_show: {str(e)}")
            traceback.print_exc()
            await interaction.followup.send(f"An error occurred while retrieving the whitelist: {str(e)}")

    async def roles_update(self, interaction: discord.Interaction, minecraft_username: str, discord_user: discord.Member = None):
        """Update a player's roles based on their Discord roles."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Use the mentioned user or the command issuer if not specified
        target_user = discord_user or interaction.user
        
        # Acknowledge the command
        await interaction.response.defer(ephemeral=False)
        
        # Run the role update
        success = await self.bot.update_minecraft_roles(target_user, minecraft_username)
        
        # Report the result
        if success:
            await interaction.followup.send(f"Successfully updated roles for Minecraft player **{minecraft_username}** based on {target_user.mention}'s Discord roles.")
        else:
            await interaction.followup.send(f"Failed to update roles for Minecraft player **{minecraft_username}**. Check the logs for details.")
    
    async def roles_check(self, interaction: discord.Interaction, discord_user: discord.Member = None):
        """Check a user's current Discord roles and mapped Minecraft roles."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Use the mentioned user or the command issuer if not specified
        target_user = discord_user or interaction.user
        
        # Acknowledge the command
        await interaction.response.defer(ephemeral=False)
        
        # Get user's Discord roles
        user_roles = target_user.roles
        
        # Create an embed to display role information
        embed = discord.Embed(
            title=f"Role Information for {target_user.display_name}",
            description=f"Discord ID: {target_user.id}",
            color=discord.Color.blue()
        )
        
        # List Discord roles
        discord_roles_str = "\n".join([f"• {role.name} (ID: {role.id})" for role in user_roles if role.name != "@everyone"])
        if discord_roles_str:
            embed.add_field(
                name="Discord Roles",
                value=discord_roles_str,
                inline=False
            )
        else:
            embed.add_field(
                name="Discord Roles",
                value="No roles assigned",
                inline=False
            )
        
        # List mapped Minecraft roles
        minecraft_roles = []
        for role in user_roles:
            if role.id in self.bot.role_mappings:
                minecraft_role = self.bot.role_mappings[role.id]
                minecraft_cmd = f"lpv user [Minecraft Username] Parent Set {minecraft_role}"
                minecraft_roles.append(f"• {role.name} -> {minecraft_role} (`{minecraft_cmd}`)")
        
        if minecraft_roles:
            embed.add_field(
                name="Mapped Minecraft Roles",
                value="\n".join(minecraft_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="Mapped Minecraft Roles",
                value="No Minecraft role mappings found for this user's Discord roles",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

    async def role_set(self, interaction: discord.Interaction, minecraft_username: str, role_name: str):
        """Directly set a specific role for a Minecraft player."""
        # Check if user has staff role
        if not any(role.id in self.bot.staff_roles for role in interaction.user.roles):
            await interaction.response.send_message(ERROR_PERMISSION_DENIED, ephemeral=True)
            return
        
        # Acknowledge the command
        await interaction.response.defer(ephemeral=False)
        
        # Validate role name - only allow specific roles
        allowed_roles = ["default", "sub", "vip", "VTuber"]
        if role_name not in allowed_roles:
            await interaction.followup.send(f"❌ Invalid role name: **{role_name}**. Allowed roles are: {', '.join(allowed_roles)}")
            return
        
        # Format and execute the lpv command
        minecraft_command = f"lpv user {minecraft_username} Parent Set {role_name}"
        
        try:
            # Execute the command
            response = await self.bot.rcon.execute_command(minecraft_command)
            
            # Check if the command was successful
            if "error" not in response.lower() and "unknown command" not in response.lower():
                await interaction.followup.send(f"✅ Successfully set role **{role_name}** for player **{minecraft_username}**.")
            else:
                await interaction.followup.send(f"❌ Failed to set role. Server response: ```{response}```")
        except Exception as e:
            print(f"Error setting role: {str(e)}")
            await interaction.followup.send(f"❌ An error occurred while setting the role: {str(e)}")

class DebugCommands(commands.Cog):
    """Debug commands for the QuingCraft bot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check if the user has staff role."""
        return any(role.id in self.bot.staff_roles for role in ctx.author.roles)
    
    @commands.command(name="debug_requests")
    async def debug_requests_command(self, ctx):
        """List all pending whitelist requests."""
        requests_info = "Current pending requests:\n"
        for user_id, msg_id in self.bot.pending_requests.items():
            # Try to get more information about the request
            request = self.bot.db.get_pending_request(user_id)
            minecraft_name = request[2] if request else "Unknown"
            requests_info += f"• User {user_id} ({minecraft_name}): Message {msg_id}\n"
        
        await ctx.send(requests_info if self.bot.pending_requests else DEBUG_NO_PENDING_REQUESTS)
    
    @commands.command(name="debug_reactions")
    async def debug_reactions_command(self, ctx, message_id: int = None):
        """Check reactions on a message."""
        if not message_id:
            await ctx.send(DEBUG_PROVIDE_MESSAGE_ID)
            return
        
        await ctx.send(DEBUG_CHECKING_REACTIONS.format(message_id=message_id))
        await self.bot.check_reactions(message_id)
    
    @commands.command(name="whitelist_force_add")
    async def whitelist_force_add_command(self, ctx, username: str = None):
        """Force add a user to the whitelist."""
        if not username:
            await ctx.send(DEBUG_PROVIDE_USERNAME)
            return
        
        await ctx.send(DEBUG_ATTEMPT_ADD.format(username=username))
        result = await self.bot.rcon.whitelist_add(username)
        await ctx.send(DEBUG_RESULT.format(result='Success' if result else 'Failed'))
    
    @commands.command(name="whitelist_check")
    async def whitelist_check_command(self, ctx, username: str = None):
        """Check if a user is on the whitelist."""
        if not username:
            await ctx.send(DEBUG_PROVIDE_USERNAME)
            return
        
        await ctx.send(DEBUG_CHECKING_WHITELIST.format(username=username))
        result = await self.bot.rcon.whitelist_check(username)
        status = WHITELIST_CHECK_ON if result else WHITELIST_CHECK_OFF
        await ctx.send(WHITELIST_CHECK_RESULT.format(username=username, status=status))

class QuingCraftBot(commands.Bot):
    """Main bot class for QuingCraft."""
    
    def __init__(self) -> None:
        """Initialize the bot with necessary components."""
        intents = discord.Intents.all()  # Use all intents
        
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
        self.rcon = RconHandler()
        self.pending_requests = {}
        self.whitelist_message_id = None
        self.role_message_id = None
        
        # Staff role IDs
        self.staff_roles = [
            int(os.getenv("ADMIN_ROLE_ID", "0")),
            int(os.getenv("MOD_ROLE_ID", "0"))
        ]
        
        # Role mappings from .env (Discord Role ID -> Minecraft Role)
        self.role_mappings = self._load_role_mappings()
        
        # Role hierarchy (higher index = higher rank)
        self.role_hierarchy = self._load_role_hierarchy()
        
        # Debug message for initialization
        print("DEBUG: Bot initialized with all intents")
    
    def _load_role_mappings(self) -> Dict[int, str]:
        """Load role mappings from environment variables."""
        role_mappings = {}
        
        # Example format in .env:
        # ROLE_MAPPING_ADMIN=12345:admin
        # ROLE_MAPPING_VIP=67890,98765:vip
        # ROLE_MAPPING_MOD=13579:mod
        #
        # The command format "lpv user {username} Parent Set {rolename}" will be used
        
        # Look for all environment variables starting with ROLE_MAPPING_
        for key, value in os.environ.items():
            if key.startswith("ROLE_MAPPING_"):
                try:
                    parts = value.split(":", 1)
                    if len(parts) != 2:
                        print(f"Invalid role mapping format for {key}: {value}")
                        continue
                    
                    discord_role_ids_str, minecraft_role = parts
                    
                    # Multiple Discord role IDs can be comma-separated
                    discord_role_ids = [int(role_id.strip()) for role_id in discord_role_ids_str.split(",")]
                    
                    for role_id in discord_role_ids:
                        role_mappings[role_id] = minecraft_role.strip()
                    
                    print(f"Loaded role mapping: {key} -> {discord_role_ids} -> {minecraft_role}")
                except Exception as e:
                    print(f"Error parsing role mapping {key}: {str(e)}")
        
        return role_mappings
    
    def _load_role_hierarchy(self) -> Dict[str, int]:
        """Load role hierarchy - higher number means higher rank."""
        hierarchy = {}
        
        # Default order based on typical naming conventions
        default_ranks = ["default", "member", "sub", "vip", "vip+", "mvp", "mvp+", "mod", "admin", "owner"]
        
        # Try to get hierarchy from environment variable
        role_hierarchy_str = os.getenv("ROLE_HIERARCHY", "")
        if role_hierarchy_str:
            try:
                # Format example: sub:1,vip:2,mod:3,admin:4
                for i, pair in enumerate(role_hierarchy_str.split(",")):
                    if not pair.strip():
                        continue
                    
                    role_name, rank_str = pair.split(":", 1)
                    rank = int(rank_str.strip())
                    hierarchy[role_name.strip().lower()] = rank
                    print(f"Added role to hierarchy: {role_name.strip().lower()} -> {rank}")
            except Exception as e:
                print(f"Error parsing role hierarchy: {str(e)}")
                print("Using default hierarchy")
                
                # If parsing fails, use default based on found roles
                known_roles = set()
                for discord_id, role_name in self.role_mappings.items():
                    known_roles.add(role_name.lower())
                
                # Create a hierarchy based on found roles and default ordering
                for i, rank in enumerate(default_ranks):
                    if rank in known_roles:
                        hierarchy[rank] = i
        else:
            print("No ROLE_HIERARCHY defined, using default order")
            # Default hierarchy based on found roles
            known_roles = set()
            for discord_id, role_name in self.role_mappings.items():
                known_roles.add(role_name.lower())
            
            # Create a hierarchy based on found roles and default ordering
            for i, rank in enumerate(default_ranks):
                if rank in known_roles:
                    hierarchy[rank] = i
        
        print(f"Role hierarchy: {hierarchy}")
        return hierarchy
    
    async def update_minecraft_roles(self, user: discord.User, minecraft_username: str, twitch_username: str = None) -> bool:
        """
        Update Minecraft roles based on Discord roles.
        
        Args:
            user: Discord user
            minecraft_username: Minecraft username
            twitch_username: Optional Twitch username
            
        Returns:
            bool: True if at least one role was updated successfully
        """
        print(f"Updating roles for {user.name} ({user.id}) with Minecraft username: {minecraft_username}")
        
        # Check if user is in our guild
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if not guild_id:
            print("No DISCORD_GUILD_ID set, cannot update roles")
            return False
        
        guild = self.get_guild(int(guild_id))
        if not guild:
            print(f"Could not find guild with ID {guild_id}")
            return False
        
        # Get the member from the guild
        member = guild.get_member(user.id)
        if not member:
            print(f"User {user.id} is not a member of the guild")
            return False
        
        # Check which roles the user has
        user_role_ids = [role.id for role in member.roles]
        
        # Track success of commands
        success_count = 0
        
        # Process Twitch integration if provided
        if twitch_username:
            print(f"Setting Twitch username {twitch_username} for {minecraft_username}")
            # Example command that could be used to link Twitch
            twitch_cmd = f"twitch link {minecraft_username} {twitch_username}"
            
            try:
                response = await self.rcon.execute_command(twitch_cmd)
                print(f"Twitch linking response: {response}")
                if "successfully" in response.lower() or "linked" in response.lower():
                    success_count += 1
            except Exception as e:
                print(f"Error linking Twitch: {str(e)}")
        
        # Find all applicable roles and their ranks
        applicable_roles = []
        for role_id in user_role_ids:
            if role_id in self.role_mappings:
                minecraft_role = self.role_mappings[role_id]
                role_rank = self.role_hierarchy.get(minecraft_role.lower(), 0)
                applicable_roles.append((minecraft_role, role_rank))
        
        # Sort roles by rank (highest rank last)
        applicable_roles.sort(key=lambda x: x[1])
        
        # Log all applicable roles
        if applicable_roles:
            roles_str = ", ".join([f"{role} (rank: {rank})" for role, rank in applicable_roles])
            print(f"User has following applicable roles: {roles_str}")
            
            # Get the highest ranked role
            highest_role, highest_rank = applicable_roles[-1]
            print(f"Using highest ranked role: {highest_role} (rank: {highest_rank})")
            
            # Apply the highest ranked role
            minecraft_command = f"lpv user {minecraft_username} Parent Set {highest_role}"
            print(f"Executing command: {minecraft_command}")
            
            try:
                response = await self.rcon.execute_command(minecraft_command)
                print(f"Role command response: {response}")
                if "error" not in response.lower() and "unknown command" not in response.lower():
                    success_count += 1
            except Exception as e:
                print(f"Error executing role command: {str(e)}")
        else:
            print(f"User {user.id} has no applicable roles")
        
        return success_count > 0

    async def add_whitelist_role(self, user_id: int) -> bool:
        """
        Add the Whitelist role to a Discord user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the whitelist role ID from environment variable
            whitelist_role_id = os.getenv("WHITELIST_ROLE_ID")
            if not whitelist_role_id:
                print("WHITELIST_ROLE_ID environment variable not set")
                return False
            
            whitelist_role_id = int(whitelist_role_id)
            
            # Get the guild
            guild_id = os.getenv("DISCORD_GUILD_ID")
            if not guild_id:
                print("DISCORD_GUILD_ID environment variable not set")
                return False
            
            guild = self.get_guild(int(guild_id))
            if not guild:
                print(f"Could not find guild with ID {guild_id}")
                return False
            
            # Get the member
            member = guild.get_member(user_id)
            if not member:
                try:
                    # Try fetching the member if not in cache
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    print(f"Member with ID {user_id} not found in guild")
                    return False
            
            # Get the role
            whitelist_role = guild.get_role(whitelist_role_id)
            if not whitelist_role:
                print(f"Could not find Whitelist role with ID {whitelist_role_id}")
                return False
            
            # Check if user already has the role
            if whitelist_role in member.roles:
                print(f"User {member.name} already has the Whitelist role")
                return True
            
            # Add the role
            await member.add_roles(whitelist_role, reason="Added to Minecraft whitelist")
            print(f"Added Whitelist role to user {member.name}")
            return True
            
        except Exception as e:
            print(f"Error adding Whitelist role: {str(e)}")
            traceback.print_exc()
            return False
    
    async def remove_whitelist_role(self, user_id: int) -> bool:
        """
        Remove the Whitelist role from a Discord user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the whitelist role ID from environment variable
            whitelist_role_id = os.getenv("WHITELIST_ROLE_ID")
            if not whitelist_role_id:
                print("WHITELIST_ROLE_ID environment variable not set")
                return False
            
            whitelist_role_id = int(whitelist_role_id)
            
            # Get the guild
            guild_id = os.getenv("DISCORD_GUILD_ID")
            if not guild_id:
                print("DISCORD_GUILD_ID environment variable not set")
                return False
            
            guild = self.get_guild(int(guild_id))
            if not guild:
                print(f"Could not find guild with ID {guild_id}")
                return False
            
            # Get the member
            member = guild.get_member(user_id)
            if not member:
                try:
                    # Try fetching the member if not in cache
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    print(f"Member with ID {user_id} not found in guild")
                    return False
            
            # Get the role
            whitelist_role = guild.get_role(whitelist_role_id)
            if not whitelist_role:
                print(f"Could not find Whitelist role with ID {whitelist_role_id}")
                return False
            
            # Check if user has the role
            if whitelist_role not in member.roles:
                print(f"User {member.name} does not have the Whitelist role")
                return True
            
            # Remove the role
            await member.remove_roles(whitelist_role, reason="Removed from Minecraft whitelist")
            print(f"Removed Whitelist role from user {member.name}")
            return True
            
        except Exception as e:
            print(f"Error removing Whitelist role: {str(e)}")
            traceback.print_exc()
            return False
    
    async def setup_hook(self) -> None:
        """Setup hook to register commands and cogs."""
        await self.add_cog(AdminCommands(self))
        await self.add_cog(DebugCommands(self))
        
        try:
            # Register global commands and sync them
            commands_synced = await self.tree.sync()
            print(f"Synced {len(commands_synced)} commands")
        except Exception as e:
            print(f"Error syncing commands: {e}")
            traceback.print_exc()
        
        @self.event
        async def on_command_error(ctx, error):
            """Default command error handler."""
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"Missing required argument: {error.param}")
            elif isinstance(error, commands.CommandNotFound):
                return
            elif isinstance(error, commands.CheckFailure):
                await ctx.send(ERROR_PERMISSION_DENIED)
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send(ERROR_PERMISSION_DENIED)
            else:
                print(f"Unhandled command error: {error}")
                traceback.print_exc()
                await ctx.send(ERROR_GENERIC)
        
        # Verify sync results
        print("Registered commands:")
        for command in self.tree.get_commands():
            print(f"/{command.name} - {command.description}")
        
        # Check global commands - but don't sync again
        global_commands = await self.tree.fetch_commands()
        print(f"Found {len(global_commands)} global commands")
        for command in global_commands:
            print(f"/{command.name} - {command.description}")
        
        # Schedule background task to cleanup old messages
        self.bg_task = self.loop.create_task(self.whitelist_command_cleanup())
        
        print("Bot setup complete")
    
    async def whitelist_command_cleanup(self) -> None:
        """Clean up duplicate slash commands and re-add them."""
        # Wait for the bot to be ready
        await self.wait_until_ready()
        
        print("Cleaning up whitelist commands...")
        
        try:
            # Delete global commands
            print("Deleting global commands...")
            global_commands = await self.tree.fetch_commands()
            for command in global_commands:
                if command.name == "qc":
                    print(f"Removing global command: {command.name} (ID: {command.id})")
                    await self.tree.delete_command(command.id)
            
            # Delete guild-specific commands
            guild_id = os.getenv("DISCORD_GUILD_ID")
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                guild_commands = await self.tree.fetch_commands(guild=guild)
                
                for command in guild_commands:
                    if command.name == "qc":
                        print(f"Removing guild command: {command.name} (ID: {command.id})")
                        await self.tree.delete_command(command.id, guild=guild)
            
            # Wait a moment to ensure commands are deleted
            await asyncio.sleep(3)
            
            # Add the AdminCommands cog with slash commands
            print("Adding AdminCommands cog...")
            admin_cog = AdminCommands(self)
            await self.add_cog(admin_cog)
            
            # Explicit sync only for the specific guild, no global sync
            if guild_id:
                print(f"Force syncing commands to guild ID: {guild_id}")
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                
                # Verify sync results
                print("Verifying guild commands...")
                guild_updated_commands = await self.tree.fetch_commands(guild=guild)
                for cmd in guild_updated_commands:
                    print(f"Registered guild command: {cmd.name} (ID: {cmd.id})")
                    if hasattr(cmd, 'children'):
                        for child in cmd.children:
                            print(f" - Child command: {child.name}")
            
            # Check global commands - but don't perform sync
            print("Verifying global commands...")
            global_updated_commands = await self.tree.fetch_commands()
            for cmd in global_updated_commands:
                print(f"Registered global command: {cmd.name} (ID: {cmd.id})")
            
        except Exception as e:
            print(f"Error during command cleanup: {e}")
            traceback.print_exc()
    
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
    
    async def create_role_message(self) -> None:
        """Create or update the role update message in the channel."""
        # Use the same channel as the whitelist message
        channel_id = int(os.getenv("WHITELIST_CHANNEL_ID"))
        channel = self.get_channel(channel_id)
        
        if not channel:
            print(f"Could not find channel with ID {channel_id}")
            return
        
        # Delete old message if it exists
        if hasattr(self, 'role_message_id') and self.role_message_id:
            try:
                old_message = await channel.fetch_message(self.role_message_id)
                await old_message.delete()
            except discord.NotFound:
                pass
        
        # Create new message
        embed = discord.Embed(
            title=ROLE_SELECTOR_TITLE,
            description=ROLE_SELECTOR_DESCRIPTION,
            color=discord.Color.green()
        )
        
        # Add info about available options
        embed.add_field(
            name=ROLE_SELECTOR_SUB_TITLE,
            value=ROLE_SELECTOR_SUB_DESCRIPTION,
            inline=False
        )
        
        embed.add_field(
            name=ROLE_SELECTOR_REQUEST_TITLE,
            value=ROLE_SELECTOR_REQUEST_DESCRIPTION,
            inline=False
        )
        
        view = RoleSelectorView(self)
        message = await channel.send(embed=embed, view=view)
        self.role_message_id = message.id
        print(f"Created role selector message with ID {message.id}")
    
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
        await self.load_pending_role_requests()
        
        # Clean up whitelist channel before creating new messages
        await self.clean_whitelist_channel()
        
        await self.create_whitelist_message()
        await self.create_role_message()
        
        # Message about command availability
        print("Commands should now be available in Discord!")
        print(f"Application ID: {self.user.id}")
        
        # Debug: List all event listeners
        print("\nDEBUG: Registered event listeners:")
        for listener in self._listeners:
            print(f" - {listener}")
    
    async def load_pending_requests(self) -> None:
        """Load pending whitelist requests from the database and try to find the associated messages."""
        try:
            # Get the moderation channel
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            mod_channel = self.get_channel(mod_channel_id)
            
            if not mod_channel:
                print(f"Could not find moderation channel with ID {mod_channel_id}")
                return
            
            # Get all pending requests from the database
            pending_requests = self.db.get_all_pending_requests()
            if not pending_requests:
                print("No pending whitelist requests found in database")
                return
            
            print(f"Found {len(pending_requests)} pending whitelist requests in database")
            
            # Initialize the pending_requests dictionary if it doesn't exist
            if not hasattr(self, 'pending_requests'):
                self.pending_requests = {}
            
            # Create a mapping of discord_ids to request objects for easier lookup
            # Index 1 should be discord_id based on the database schema
            requests_by_id = {request[1]: request for request in pending_requests}
            
            # Fetch up to 200 messages from the moderation channel to find relevant ones
            async for message in mod_channel.history(limit=200):
                if not message.embeds:
                    continue
                
                embed = message.embeds[0]
                
                # Find whitelist request messages
                if hasattr(embed, 'title') and embed.title == MOD_REQUEST_TITLE:
                    # Extract the discord_id from the embed
                    try:
                        description = embed.description
                        match = re.search(r'<@(\d+)>', description)
                        if match:
                            discord_id = int(match.group(1))
                            
                            # Check if this user has a pending request
                            if discord_id in requests_by_id:
                                request = requests_by_id[discord_id]
                                # Store the request in memory with the message_id for future processing
                                # Index 2 should be minecraft_username based on the database schema
                                minecraft_username = request[2]
                                self.pending_requests[discord_id] = message.id
                                print(f"Associated request for {discord_id} with message {message.id}")
                                
                                # Remove from our mapping so we can track which ones weren't found
                                requests_by_id.pop(discord_id, None)
                    except Exception as e:
                        print(f"Error processing embed in message {message.id}: {str(e)}")
                        traceback.print_exc()
                    
            # Log any requests for which we couldn't find messages
            if requests_by_id:
                print(f"Could not find messages for {len(requests_by_id)} requests: {list(requests_by_id.keys())}")
            
            print(f"Loaded {len(self.pending_requests)} whitelist requests into memory")
            
        except Exception as e:
            print(f"Error loading pending requests: {str(e)}")
            traceback.print_exc()

    async def load_pending_role_requests(self) -> None:
        """Load pending role requests from the database and try to find the associated messages."""
        try:
            # Get the moderation channel
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            mod_channel = self.get_channel(mod_channel_id)
            
            if not mod_channel:
                print(f"Could not find moderation channel with ID {mod_channel_id}")
                return
            
            # Get all pending role requests from the database
            pending_role_requests = self.db.get_all_pending_role_requests()
            if not pending_role_requests:
                print("No pending role requests found in database")
                return
            
            print(f"Found {len(pending_role_requests)} pending role requests in database")
            
            # Initialize the role_requests dictionary if it doesn't exist
            if not hasattr(self, 'role_requests'):
                self.role_requests = {}
            
            # Create a mapping of discord_ids to request objects for easier lookup
            # Index 1 should be discord_id based on the database schema
            requests_by_id = {request[1]: request for request in pending_role_requests}
            
            # Count messages found by message_id and by searching
            found_by_id = 0
            found_by_search = 0
            
            # First, try to load requests directly from message IDs
            for discord_id, request in requests_by_id.copy().items():
                # Index 9 should be message_id based on the database schema
                if request[9]:
                    try:
                        # Try to fetch the message directly by ID
                        message = await mod_channel.fetch_message(request[9])
                        # Index 2 should be minecraft_username, Index 3 should be requested_role
                        minecraft_username = request[2]
                        requested_role = request[3]
                        self.role_requests[discord_id] = (message.id, minecraft_username, requested_role)
                        found_by_id += 1
                        requests_by_id.pop(discord_id, None)
                        continue
                    except Exception as e:
                        print(f"Could not find message by ID {request[9]} for role request {discord_id}: {str(e)}")
            
            # For any remaining requests, search through recent messages
            if requests_by_id:
                async for message in mod_channel.history(limit=200):
                    if not message.embeds:
                        continue
                        
                    embed = message.embeds[0]
                    
                    # Find role request messages
                    if hasattr(embed, 'title') and embed.title == ROLE_REQUEST_TITLE:
                        # Extract the discord_id from the embed
                        try:
                            description = embed.description
                            match = re.search(r'<@(\d+)>', description)
                            if match:
                                discord_id = int(match.group(1))
                                
                                # Check if this user has a pending request
                                if discord_id in requests_by_id:
                                    request = requests_by_id[discord_id]
                                    # Store the request in memory with the message_id for future processing
                                    # Index 2 should be minecraft_username, Index 3 should be requested_role
                                    minecraft_username = request[2]
                                    requested_role = request[3]
                                    self.role_requests[discord_id] = (message.id, minecraft_username, requested_role)
                                    found_by_search += 1
                                    
                                    # Update the message_id in the database
                                    self.db.update_role_request_message_id(discord_id, message.id)
                                    
                                    # Remove from our mapping so we can track which ones weren't found
                                    requests_by_id.pop(discord_id, None)
                        except Exception as e:
                            print(f"Error processing embed in message {message.id} for role requests: {str(e)}")
                            traceback.print_exc()
            
            # Log any requests for which we couldn't find messages
            if requests_by_id:
                print(f"Could not find messages for {len(requests_by_id)} role requests: {list(requests_by_id.keys())}")
            
            print(f"Loaded {len(self.role_requests)} role requests into memory (by ID: {found_by_id}, by search: {found_by_search})")
            
        except Exception as e:
            print(f"Error loading pending role requests: {str(e)}")
            traceback.print_exc()
    
    async def clean_whitelist_channel(self) -> None:
        """Delete all bot messages from the whitelist channel."""
        try:
            channel_id = int(os.getenv("WHITELIST_CHANNEL_ID"))
            channel = self.get_channel(channel_id)
            
            if not channel:
                print(f"Could not find whitelist channel with ID {channel_id}")
                return
                
            print(f"Cleaning whitelist channel {channel.name}...")
            
            # Get the bot's user ID
            bot_id = self.user.id
            deleted_count = 0
            
            # Find and delete all messages from the bot
            async for message in channel.history(limit=100):
                if message.author.id == bot_id:
                    try:
                        await message.delete()
                        deleted_count += 1
                        # Add a small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                    except discord.errors.NotFound:
                        pass
                    except Exception as e:
                        print(f"Error deleting message: {e}")
            
            print(f"Deleted {deleted_count} messages from whitelist channel.")
        except Exception as e:
            print(f"Error cleaning whitelist channel: {e}")
            traceback.print_exc()

    # Keep only one event listener for on_message
    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages and commands."""
        if message.author.bot:
            return
        
        # Debug commands
        if message.content.startswith("!debug"):
            # Check if user has staff role
            if not any(role.id in self.staff_roles for role in message.author.roles):
                return  # Silently ignore debug commands from non-staff users
            
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
            elif message.content == "!debug-recreate":
                await self._debug_recreate_messages(message)
            elif message.content.startswith("!debug-memory"):
                # Show important variables and their content
                memory_info = "**Memory Debug:**\n"
                memory_info += f"- pending_requests: {self.pending_requests}\n"
                memory_info += f"- whitelist_message_id: {self.whitelist_message_id}\n"
                memory_info += f"- role_message_id: {getattr(self, 'role_message_id', None)}\n"
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
            # Try to get more information about the request
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
            await message.channel.send(DEBUG_CHECKING_REACTIONS.format(message_id=message_id))
            await self.check_reactions(message_id)
        except ValueError:
            await message.channel.send("Invalid message ID. Please provide a valid number.")
    
    # Event listener for reactions
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds."""
        # Ignore bot reactions
        if payload.user_id == self.user.id:
            return
        
        # Check if it's a reaction on a whitelist request
        found_request = False
        
        # Check whitelist requests first using in-memory dictionary
        for user_id, message_id in self.pending_requests.items():
            if message_id == payload.message_id:
                found_request = True
                await self._handle_whitelist_reaction(payload, user_id, message_id)
                break
        
        # If not found, check if it's a reaction on a mod channel message with embed
        if not found_request:
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            
            # Only proceed if we're in the mod channel
            if payload.channel_id == mod_channel_id:
                try:
                    # Get the channel and message
                    channel = self.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    
                    # Check if it has embeds and is a whitelist request
                    if message.embeds and message.embeds[0].title == MOD_REQUEST_TITLE:
                        # Extract the Discord user ID from the embed
                        import re
                        match = re.search(r"Discord: <@(\d+)>", message.embeds[0].description)
                        if match:
                            user_id = int(match.group(1))
                            
                            # Check if this user has a pending request in database
                            request = self.db.get_pending_request(user_id)
                            if request:
                                # Store it in memory for future use
                                self.pending_requests[user_id] = message.id
                                print(f"Found pending request for user {user_id} during reaction processing")
                                
                                # Process the reaction
                                found_request = True
                                await self._handle_whitelist_reaction(payload, user_id, message.id)
                except Exception as e:
                    print(f"Error processing reaction on potential whitelist message: {e}")
                    traceback.print_exc()
        
        # If still not found, check role requests
        if not found_request and hasattr(self, 'role_requests'):
            for user_id, (message_id, minecraft_username, requested_role) in self.role_requests.items():
                if message_id == payload.message_id:
                    found_request = True
                    await self._handle_role_request_reaction(payload, user_id, minecraft_username, requested_role)
                    break

    async def _handle_whitelist_reaction(self, payload, user_id, message_id):
        """Handle reactions on whitelist requests."""
        # Get channel and message
        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        # Get the user who reacted (moderator)
        guild = self.get_guild(payload.guild_id)
        moderator = guild.get_member(payload.user_id)
        
        # Check if the reactor has staff role
        if not any(role.id in self.staff_roles for role in moderator.roles):
            # Remove the reaction if not staff
            for reaction in message.reactions:
                if reaction.emoji in ["✅", "❌"]:
                    await reaction.remove(moderator)
            return
        
        # Get the requestor
        requestor = guild.get_member(user_id)
        if not requestor:
            await channel.send(f"Error: Could not find user with ID {user_id}")
            return
        
        # Handle approval
        if payload.emoji.name == "✅":
            print(f"[REACTION] Processing approval for user {user_id} by moderator {moderator.display_name}")
            await self._approve_whitelist_request_with_mod(user_id, payload.channel_id, payload.user_id)
        elif payload.emoji.name == "❌":
            print(f"[REACTION] Processing rejection for user {user_id} by moderator {moderator.display_name}")
            await self._reject_whitelist_request_with_mod(user_id, payload.user_id)
    
    async def _approve_whitelist_request_with_mod(self, user_id: int, channel_id: int, moderator_id: int) -> None:
        """Approve a whitelist request with moderator ID."""
        try:
            # Get the request from the database
            request = self.db.get_pending_request(user_id)
            if not request:
                print(f"DEBUG: No pending request found for user {user_id}")
                return
            
            request_id = request[0]
            minecraft_username = request[2]
            print(f"DEBUG: Processing whitelist approval for {minecraft_username} by moderator {moderator_id}")
            
            # Try to add the player to the whitelist
            print(f"DEBUG: Adding {minecraft_username} to whitelist")
            success = await self.rcon.whitelist_add(minecraft_username)
            
            if success:
                print(f"DEBUG: Successfully added {minecraft_username} to whitelist")
                
                # Update the request status with the moderator ID
                db_success = self.db.update_request_status(request_id, "approved", moderator_id)
                print(f"DEBUG: Database update result: {db_success}")
                
                # Add Discord whitelist role to the user
                await self.add_whitelist_role(user_id)
                
                # Remove from pending requests
                if user_id in self.pending_requests:
                    del self.pending_requests[user_id]
                
                # Notify the user
                try:
                    discord_user = await self.fetch_user(user_id)
                    if discord_user:
                        await discord_user.send(WHITELIST_APPROVED.format(username=minecraft_username))
                        print(f"DEBUG: Sent approval message to user {user_id}")
                except Exception as e:
                    print(f"DEBUG: Error sending message to user: {str(e)}")
            else:
                print(f"DEBUG: Failed to add {minecraft_username} to whitelist")
                
                # Notify the moderator about the problem
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
            # Get the request from the database
            request = self.db.get_pending_request(user_id)
            if not request:
                print(f"DEBUG: No pending request found for user {user_id}")
                return
            
            request_id = request[0]
            minecraft_username = request[2]
            print(f"DEBUG: Processing whitelist rejection for {minecraft_username} by moderator {moderator_id}")
            
            # Update the request status with the moderator ID
            db_success = self.db.update_request_status(request_id, "rejected", moderator_id)
            print(f"DEBUG: Database update result: {db_success}")
            
            # Remove Discord whitelist role if it exists
            await self.remove_whitelist_role(user_id)
            
            # Remove from pending requests
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]
            
            # Notify the user
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
    
    async def check_reactions(self, message_id: int) -> None:
        """Check reactions on a specific message."""
        try:
            mod_channel_id = int(os.getenv("MOD_CHANNEL_ID"))
            mod_channel = self.get_channel(mod_channel_id)
            
            if not mod_channel:
                print(f"Could not find mod channel with ID {mod_channel_id}")
                return
            
            try:
                message = await mod_channel.fetch_message(message_id)
            except discord.NotFound:
                print(f"Message {message_id} not found in channel {mod_channel_id}")
                return
            
            if not message.reactions:
                print(f"No reactions on message {message_id}")
                return
            
            print(f"Found {len(message.reactions)} reactions on message {message_id}")
            
            for reaction in message.reactions:
                print(f"Reaction: {reaction.emoji}, count: {reaction.count}")
                async for user in reaction.users():
                    print(f"- User: {user.name} ({user.id})")
        except Exception as e:
            print(f"Error checking reactions: {str(e)}")
            traceback.print_exc()

    async def _handle_role_request_reaction(self, payload, user_id, minecraft_username, requested_role):
        """Handle reactions on role requests."""
        # Get channel and message
        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        # Get the user who reacted (moderator)
        guild = self.get_guild(payload.guild_id)
        moderator = guild.get_member(payload.user_id)
        
        # Check if the reactor has staff role
        if not any(role.id in self.staff_roles for role in moderator.roles):
            # Remove the reaction if not staff
            for reaction in message.reactions:
                if reaction.emoji in ["✅", "❌"]:
                    await reaction.remove(moderator)
            return
        
        # Get the requestor
        requestor = guild.get_member(user_id)
        if not requestor:
            await channel.send(f"Error: Could not find user with ID {user_id}")
            return
        
        # Handle approval
        if payload.emoji.name == "✅":
            print(f"[ROLE] Processing approval for {requested_role} role for {minecraft_username}")
            
            # Validate that the requested role is allowed
            allowed_roles = ["default", "sub", "vip", "VTuber"]
            if requested_role not in allowed_roles:
                await channel.send(f"❌ Cannot approve role request: **{requested_role}** is not an allowed role. Allowed roles are: {', '.join(allowed_roles)}")
                # Remove the approval reaction
                for reaction in message.reactions:
                    if reaction.emoji == "✅":
                        await reaction.remove(moderator)
                return
            
            try:
                # Add the role to the user in-game using lpv
                rcon_response = await self.rcon.execute_command(f"lpv user {minecraft_username} parent set {requested_role}")
                
                # Update the embed to indicate approval
                embed = message.embeds[0]
                embed.color = discord.Color.green()
                embed.set_footer(text=f"Approved by {moderator.display_name} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
                await message.edit(embed=embed)
                
                # Notify the user
                await requestor.send(ROLE_REQUEST_APPROVED.format(role=requested_role, username=minecraft_username))
                
                # Remove the request from our tracking
                if user_id in self.role_requests:
                    del self.role_requests[user_id]
                    
                # Log the approval
                print(f"[ROLE] Role request approved: {minecraft_username} -> {requested_role}")
                
            except Exception as e:
                print(f"[ROLE] Error approving role request: {e}")
                await channel.send(ROLE_ERROR_APPROVAL.format(error=str(e)))
        
        elif payload.emoji.name == "❌":
            print(f"[ROLE] Processing rejection for {requested_role} role for {minecraft_username}")
            
            try:
                # Update the embed to indicate rejection
                embed = message.embeds[0]
                embed.color = discord.Color.red()
                embed.set_footer(text=f"Rejected by {moderator.display_name} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
                await message.edit(embed=embed)
                
                # Notify the user
                await requestor.send(ROLE_REQUEST_REJECTED.format(role=requested_role))
                
                # Remove the request from our tracking
                if user_id in self.role_requests:
                    del self.role_requests[user_id]
                    
                # Log the rejection
                print(f"[ROLE] Role request rejected: {minecraft_username} -> {requested_role}")
                
            except Exception as e:
                print(f"[ROLE] Error rejecting role request: {e}")
                await channel.send(ROLE_ERROR_REJECTION.format(error=str(e)))

    async def _debug_recreate_messages(self, message):
        """Force recreate whitelist and role messages."""
        await message.channel.send("Recreating whitelist and role messages...")
        
        # Delete old messages if they exist
        channel_id = int(os.getenv("WHITELIST_CHANNEL_ID"))
        channel = self.get_channel(channel_id)
        
        if not channel:
            await message.channel.send(f"Could not find channel with ID {channel_id}")
            return
        
        # Delete old whitelist message
        if self.whitelist_message_id:
            try:
                old_message = await channel.fetch_message(self.whitelist_message_id)
                await old_message.delete()
                self.whitelist_message_id = None
            except discord.NotFound:
                pass
        
        # Delete old role message
        if hasattr(self, 'role_message_id') and self.role_message_id:
            try:
                old_message = await channel.fetch_message(self.role_message_id)
                await old_message.delete()
                self.role_message_id = None
            except discord.NotFound:
                pass
        
        # Create new messages
        await self.create_whitelist_message()
        await self.create_role_message()
        
        await message.channel.send("Messages recreated successfully!")

def main() -> None:
    """Start the bot."""
    bot = QuingCraftBot()
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    main() 