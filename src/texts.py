"""
Text messages used by the QuingCraft Discord bot.
"""

# Whitelist messages
WHITELIST_TITLE = "QuingCraft Server Whitelist"
WHITELIST_DESCRIPTION = "Welcome to QuingCraft! To access our Minecraft server, you'll need to be added to our whitelist. Click the button below to submit your request. Please ensure you enter your correct Minecraft Java Edition username."
WHITELIST_INVALID_NAME = "The Minecraft username you provided appears to be invalid. Please double-check the spelling and ensure you're using your Java Edition account name."
WHITELIST_SUCCESS = "Your whitelist request has been successfully submitted! ✅\n\nA staff member will review it as soon as possible. You'll receive a notification once your request has been processed."
WHITELIST_APPROVED = "🎉 Great news! Your whitelist request has been approved! You can now join our Minecraft server as **{username}**.\n\n**Server Address:** quingcraft.niklasky.com"
WHITELIST_REJECTED = "We're sorry, but your whitelist request has been declined. If you have any questions or would like to appeal this decision, please contact a staff member."
WHITELIST_PENDING = "You already have a pending whitelist request. Please wait for it to be processed before submitting a new one. Our staff reviews requests as quickly as possible."
WHITELIST_DUPLICATE = "There's already a pending request for this Minecraft username. If this is your account, please wait for your request to be processed. If you believe this is an error, please contact a staff member."

# Moderation messages
MOD_REQUEST_TITLE = "📝 New Whitelist Request"
MOD_REQUEST_DESCRIPTION = "**Minecraft Username:** {minecraft_username}\n**Discord:** {discord_user}\n**Account Created:** {account_created}\n**Joined Server:** {joined_server}"
MOD_ACCEPT = "✅ Approve"
MOD_REJECT = "❌ Decline"
MOD_ACCEPTED = "Your whitelist request has been approved! You can now join our Minecraft server. Enjoy your time on QuingCraft!"
MOD_REJECTED = "Your whitelist request has been declined. If you have any questions, please contact a staff member."
MOD_ERROR_WHITELIST = "⚠️ Error adding {username} to the whitelist. Please try again manually or contact an administrator."

# Error messages
ERROR_DATABASE = "⚠️ Database error. Unable to process your request at this time. Please try again later or contact an administrator."
ERROR_PROCESSING = "⚠️ An unexpected error occurred while processing your request. Please try again or contact an administrator if the issue persists."
ERROR_PERMISSION_DENIED = "⛔ You don't have permission to use this command. This action is restricted to staff members."
ERROR_GENERIC = "⚠️ Something went wrong. Please try again later or contact a staff member for assistance."
ERROR_RCON = "⚠️ Failed to communicate with the Minecraft server. Please contact an administrator to resolve this issue."

# Command responses
WHITELIST_COMMAND_SUCCESS = "Command executed successfully:\n```{response}```"
WHITELIST_ADD_SUCCESS = "✅ Successfully added **{username}** to the whitelist."
WHITELIST_REMOVE_SUCCESS = "✅ Successfully removed **{username}** from the whitelist."
WHITELIST_CHECK_RESULT = "**{username}** is {status} the whitelist."
WHITELIST_CHECK_ON = "on"
WHITELIST_CHECK_OFF = "not on"
DEBUG_PROVIDE_USERNAME = "Please provide a Minecraft username to continue."
DEBUG_ATTEMPT_ADD = "Attempting to add **{username}** to the whitelist..."
DEBUG_RESULT = "Result: {result}"
DEBUG_PROVIDE_MESSAGE_ID = "Please provide a message ID to check reactions."
DEBUG_CHECKING_REACTIONS = "Checking reactions on message {message_id}..."
DEBUG_CHECKING_WHITELIST = "Checking if **{username}** is on the whitelist..."
DEBUG_NO_PENDING_REQUESTS = "There are no pending whitelist requests."
DEBUG_INVALID_MESSAGE_ID = "Invalid message ID. Please provide a valid number."

# Role selector view texts
ROLE_SELECTOR_TITLE = "Minecraft Role Manager"
ROLE_SELECTOR_DESCRIPTION = "Manage your in-game roles using the options below. Note: You must have joined the server at least once before you can request or receive any role."
ROLE_SELECTOR_SUB_TITLE = "🌟 Subscriber Benefits"
ROLE_SELECTOR_SUB_DESCRIPTION = "Twitch subscribers can claim the Subscriber role in-game for exclusive perks. Use the **Get Sub Role** button to link your accounts."
ROLE_SELECTOR_REQUEST_TITLE = "🏆 Special Roles"
ROLE_SELECTOR_REQUEST_DESCRIPTION = "Need a special role? Currently, we offer **VIP** and **VTuber** roles. Use the **Request Special Role** button to submit a request to our staff team."

# Role request messages
ROLE_REQUEST_TITLE = "🏆 Special Role Request"
ROLE_REQUEST_DESCRIPTION = "Submit a request for a special role on our Minecraft server."
ROLE_REQUEST_INVALID_NAME = "Invalid Minecraft username. Please check that you've entered your correct Java Edition username."
ROLE_REQUEST_SUCCESS = "Your request for the **{role}** role has been submitted to our staff team! You'll receive a notification when your request has been processed."
ROLE_REQUEST_APPROVED = "🎉 Congratulations! Your request for the **{role}** role has been approved. The role has been assigned to your Minecraft account **{username}**."
ROLE_REQUEST_REJECTED = "We're sorry, but your request for the **{role}** role has been declined. If you have any questions, please contact a staff member."
ROLE_ERROR_APPROVAL = "⚠️ Error approving role request: {error}"
ROLE_ERROR_REJECTION = "⚠️ Error rejecting role request: {error}"
ROLE_SUB_ERROR = "⚠️ Error: Subscriber role configuration is missing. Please contact a staff member for assistance."
ROLE_NO_SUB = "You need an active Twitch subscription to claim the Subscriber role. Please ensure you've linked your Twitch account and have an active subscription to Quingcraft." 