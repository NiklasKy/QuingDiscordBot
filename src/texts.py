"""
Contains all text messages used by the bot.
"""

# Whitelist messages
WHITELIST_TITLE = "Whitelist Request"
WHITELIST_DESCRIPTION = "Please react with 🎮 to start the whitelist process."
WHITELIST_INVALID_NAME = "Invalid Minecraft username. Please try again."
WHITELIST_SUCCESS = "Your whitelist request has been submitted for review."
WHITELIST_APPROVED = "Your whitelist request has been approved! You can now join the server as {username}."
WHITELIST_REJECTED = "Your whitelist request has been rejected. Please contact a moderator for more information."
WHITELIST_PENDING = "You already have a pending whitelist request."

# Moderation messages
MOD_REQUEST_TITLE = "New Whitelist Request"
MOD_REQUEST_DESCRIPTION = "User: {discord_user}\nMinecraft Username: {minecraft_username}"
MOD_ACCEPT = "✅ Accept"
MOD_REJECT = "❌ Reject"
MOD_ACCEPTED = "Your whitelist request has been accepted! You can now join the server."
MOD_REJECTED = "Your whitelist request has been rejected. Please contact a moderator for more information."

# Error messages
ERROR_GENERIC = "An error occurred. Please try again later."
ERROR_DATABASE = "Database error occurred. Please contact an administrator."
ERROR_RCON = "Failed to communicate with the Minecraft server. Please contact an administrator." 