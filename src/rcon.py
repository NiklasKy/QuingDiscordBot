"""
RCON connection handler for Minecraft server commands.
"""
import os
import logging
import asyncio
from typing import Optional, Tuple
import mcrcon
from dotenv import load_dotenv
import time

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
            
            # If offline player, wait longer for UUID fetch from Mojang
            if "offline" in response.lower() or "fetching uuid" in response.lower():
                logger.info(f"Player {username} is offline, waiting for UUID fetch...")
                start_time = time.time()
                logger.info(f"Starting first wait at {time.strftime('%H:%M:%S')} (5 seconds)")
                await asyncio.sleep(5)  # Initial wait
                end_time = time.time()
                logger.info(f"Finished first wait at {time.strftime('%H:%M:%S')} (actual duration: {end_time - start_time:.2f}s)")
                
                # First check after wait
                if await self.whitelist_check(username):
                    logger.info(f"{username} was added to the whitelist after first wait")
                    return True
                
                # If still not on the list, wait longer and check again (Mojang API can be slow)
                logger.info(f"Player {username} not yet on whitelist, waiting longer...")
                start_time = time.time()
                logger.info(f"Starting second wait at {time.strftime('%H:%M:%S')} (10 seconds)")
                await asyncio.sleep(10)
                end_time = time.time()
                logger.info(f"Finished second wait at {time.strftime('%H:%M:%S')} (actual duration: {end_time - start_time:.2f}s)")
                
                if await self.whitelist_check(username):
                    logger.info(f"{username} was added to the whitelist after second wait")
                    return True
                
                # One more check with longer wait
                logger.info(f"Player {username} not yet on whitelist, final wait...")
                start_time = time.time()
                logger.info(f"Starting final wait at {time.strftime('%H:%M:%S')} (15 seconds)")
                await asyncio.sleep(15)
                end_time = time.time()
                logger.info(f"Finished final wait at {time.strftime('%H:%M:%S')} (actual duration: {end_time - start_time:.2f}s)")
                
                if await self.whitelist_check(username):
                    logger.info(f"{username} was added to the whitelist after final wait")
                    return True
                
                # If the whitelisting was still not successful after waiting,
                # but there was no error in the response, consider it a success anyway
                if "error" not in response.lower() and "unknown command" not in response.lower():
                    logger.warning(f"Player {username} not detected in whitelist, but assuming success based on RCON response")
                    return True
            else:
                # For online players, a shorter wait should be enough
                await asyncio.sleep(2)
                
                # Check if player was added
                if await self.whitelist_check(username):
                    logger.info(f"{username} was added to the whitelist")
                    return True
                
                # If explicit success message
                if "added" in response.lower():
                    logger.info(f"{username} was considered added to the whitelist based on response")
                    return True
            
            # If we got here, try again
            logger.warning(f"Failed to add {username} to the whitelist, retrying")
            response = await self.execute_command(f"vpw add {username}")
            logger.info(f"Whitelist add retry response: {response}")
            
            # Wait after retry
            await asyncio.sleep(5)
            
            # Check again
            if await self.whitelist_check(username):
                logger.info(f"{username} was added to the whitelist after retry")
                return True
            
            # If the response indicates success but check fails, trust the response
            if "added" in response.lower() or ("fetching uuid" in response.lower() and "error" not in response.lower()):
                logger.warning(f"Player {username} not detected in whitelist, but assuming success based on retry response")
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
            
            # Wait for the server to process the removal
            await asyncio.sleep(3)
            
            # Verify the player was removed
            if not await self.whitelist_check(username):
                logger.info(f"{username} was removed from the whitelist")
                return True
            
            # If the response indicates a successful removal, return success
            if "removed" in response.lower():
                logger.info(f"{username} was considered removed from the whitelist based on response")
                return True
            
            # Wait a bit longer and check again
            logger.info(f"Player {username} still appears on whitelist, waiting longer...")
            await asyncio.sleep(5)
            
            if not await self.whitelist_check(username):
                logger.info(f"{username} was removed from the whitelist after waiting")
                return True
            
            # If the list command is unreliable, we'll assume success if the command executed without errors
            if "error" not in response.lower() and "unknown command" not in response.lower():
                logger.warning(f"Player {username} still detected in whitelist, but assuming success based on RCON response")
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
            
            # Add more detailed debug logging
            if username.lower() in response.lower():
                logger.info(f"Player {username} found in whitelist")
                return True
            else:
                logger.info(f"Player {username} NOT found in whitelist. Full response: '{response}'")
                # Check if the response is empty or says no players
                if "no players" in response.lower() or not response.strip():
                    logger.info("Whitelist appears to be empty or command returned no players")
                
                return False
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