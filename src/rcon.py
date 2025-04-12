"""
RCON connection handler for Minecraft server commands.
"""
import os
import logging
import asyncio
from typing import Optional, Tuple
import mcrcon
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RconHandler:
    """Handles RCON connections and commands for the Minecraft server."""
    
    def __init__(self) -> None:
        """Initialize RCON connection parameters."""
        # Verwende host.docker.internal statt der Umgebungsvariable
        self.host = "host.docker.internal"
        self.port = int(os.getenv("RCON_PORT", "25575"))
        self.password = os.getenv("RCON_PASSWORD")
        self.rcon = mcrcon.MCRcon(self.host, self.password, self.port)
        logger.info(f"Initialized RCON handler for {self.host}:{self.port}")
    
    async def whitelist_add(self, username: str) -> bool:
        """
        Add a player to the whitelist
        
        Args:
            username: The username to add to the whitelist
            
        Returns:
            bool: True if the player was added, False otherwise
        """
        logger.info(f"Adding {username} to the whitelist")
        
        # Check if already whitelisted
        if await self.whitelist_check(username):
            logger.info(f"{username} is already on the whitelist")
            return True
        
        # Try to add the player to the whitelist
        try:
            response = await self.execute_command(f"vpw add {username}")
            logger.info(f"Whitelist add response: {response}")
            
            # Verify the player was added
            if await self.whitelist_check(username):
                logger.info(f"{username} was added to the whitelist")
                return True
            
            # If player is offline, the command might fail, try again
            logger.warning(f"Failed to add {username} to the whitelist, retrying")
            response = await self.execute_command(f"vpw add {username}")
            logger.info(f"Whitelist add retry response: {response}")
            
            # Check again
            if await self.whitelist_check(username):
                logger.info(f"{username} was added to the whitelist after retry")
                return True
            
            logger.error(f"Failed to add {username} to the whitelist after retry")
            return False
        except Exception as e:
            logger.error(f"Error adding {username} to the whitelist: {e}")
            return False
    
    async def whitelist_remove(self, username: str) -> bool:
        """
        Remove a player from the whitelist
        
        Args:
            username: The username to remove from the whitelist
            
        Returns:
            bool: True if the player was removed, False otherwise
        """
        logger.info(f"Removing {username} from the whitelist")
        
        # Check if already not on the whitelist
        if not await self.whitelist_check(username):
            logger.info(f"{username} is not on the whitelist")
            return True
        
        # Try to remove the player from the whitelist
        try:
            response = await self.execute_command(f"vpw remove {username}")
            logger.info(f"Whitelist remove response: {response}")
            
            # Verify the player was removed
            if not await self.whitelist_check(username):
                logger.info(f"{username} was removed from the whitelist")
                return True
            
            logger.error(f"Failed to remove {username} from the whitelist")
            return False
        except Exception as e:
            logger.error(f"Error removing {username} from the whitelist: {e}")
            return False
    
    async def whitelist_check(self, username: str) -> bool:
        """
        Check if a player is on the whitelist
        
        Args:
            username: The username to check
            
        Returns:
            bool: True if the player is on the whitelist, False otherwise
        """
        logger.info(f"Checking if {username} is on the whitelist")
        
        try:
            response = await self.execute_command(f"vpw list")
            logger.info(f"Whitelist check response: {response}")
            
            # Parse the response and check if the username is in it
            return username.lower() in response.lower()
        except Exception as e:
            logger.error(f"Error checking if {username} is on the whitelist: {e}")
            return False

    async def execute_command(self, command: str) -> str:
        """Execute a custom RCON command."""
        try:
            logger.info(f"Executing command: {command}")
            self.rcon.connect()
            # Direkter Befehl ohne Präfix
            response = self.rcon.command(command)
            logger.info(f"RCON response: {response}")
            return response
        except ConnectionRefusedError:
            logger.error("RCON connection refused. Is the Minecraft server running?")
            return "Error: Connection refused"
        except TimeoutError:
            logger.error("RCON connection timed out. Is the server reachable?")
            return "Error: Connection timeout"
        except Exception as e:
            logger.error(f"RCON error: {str(e)}")
            return f"Error: {str(e)}"
        finally:
            try:
                self.rcon.disconnect()
            except:
                pass 