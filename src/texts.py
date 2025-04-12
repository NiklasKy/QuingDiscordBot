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
MOD_REQUEST_DESCRIPTION = "Whitelist request for {minecraft_username}\nDiscord: {discord_user}\nAccount created: {account_created}\nJoined server: {joined_server}"
MOD_ACCEPT = "✅ Accept"
MOD_REJECT = "❌ Reject"
MOD_ACCEPTED = "Your whitelist request has been accepted! You can now join the server."
MOD_REJECTED = "Your whitelist request has been rejected. Please contact a moderator for more information."
MOD_ERROR_WHITELIST = "⚠️ Error adding {username} to the whitelist. Please try manually or contact the administrator."

# Error messages
ERROR_DATABASE = "There was an error accessing the database. Please try again later."
ERROR_PROCESSING = "An error occurred. Please try again later or contact an administrator."
ERROR_PERMISSION_DENIED = "You don't have permission to use this command."
ERROR_GENERIC = "An error occurred. Please try again later."
ERROR_RCON = "Failed to communicate with the Minecraft server. Please contact an administrator."

# Command responses
WHITELIST_COMMAND_SUCCESS = "Whitelist command executed:\n```{response}```"
WHITELIST_ADD_SUCCESS = "Successfully added {username} to the whitelist."
WHITELIST_REMOVE_SUCCESS = "Successfully removed {username} from the whitelist."
WHITELIST_CHECK_RESULT = "{username} is {status} the whitelist."
WHITELIST_CHECK_ON = "on"
WHITELIST_CHECK_OFF = "not on"
DEBUG_PROVIDE_USERNAME = "Please provide a Minecraft username."
DEBUG_ATTEMPT_ADD = "Attempting to add {username} to whitelist..."
DEBUG_RESULT = "Result: {result}"
DEBUG_PROVIDE_MESSAGE_ID = "Please provide a message ID to check."
DEBUG_CHECKING_REACTIONS = "Checking reactions on message {message_id}..."
DEBUG_CHECKING_WHITELIST = "Checking if {username} is on the whitelist..."
DEBUG_NO_PENDING_REQUESTS = "No pending requests."
DEBUG_INVALID_MESSAGE_ID = "Invalid message ID. Please provide a valid number." 