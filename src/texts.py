"""
Contains all text messages used by the bot.
"""

# Whitelist messages
WHITELIST_TITLE = "Whitelist Request"
WHITELIST_DESCRIPTION = "Click the button below to request whitelist access."
WHITELIST_INVALID_NAME = "Invalid Minecraft username. Please check the spelling."
WHITELIST_SUCCESS = "Your whitelist request has been submitted! You will be notified once it has been processed."
WHITELIST_APPROVED = "Your whitelist request has been approved! You can now join the server as {username}."
WHITELIST_REJECTED = "Your whitelist request has been rejected. Please contact a moderator for more information."
WHITELIST_PENDING = "You already have a pending whitelist request. Please wait until it is processed."
WHITELIST_DUPLICATE = "There is already a pending request for this username. Please choose a different name or wait until the existing request has been processed."

# Moderation messages
MOD_REQUEST_TITLE = "New Whitelist Request"
MOD_REQUEST_DESCRIPTION = "User: {discord_user}\nMinecraft Username: {minecraft_username}"
MOD_ACCEPT = "✅ Accept"
MOD_REJECT = "❌ Reject"
MOD_ACCEPTED = "Your whitelist request has been accepted! You can now join the server."
MOD_REJECTED = "Your whitelist request has been rejected. Please contact a moderator for more information."
MOD_ERROR_WHITELIST = "⚠️ Error adding {username} to the whitelist. Please try manually or contact the administrator."

# Error messages
ERROR_GENERIC = "An error occurred. Please try again later."
ERROR_DATABASE = "A database error occurred. Please contact an administrator."
ERROR_RCON = "Failed to communicate with the Minecraft server. Please contact an administrator."
ERROR_PROCESSING = "An error occurred. Please try again later or contact an administrator." 