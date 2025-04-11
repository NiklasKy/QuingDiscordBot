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
        """Add a player to the server whitelist."""
        try:
            logger.info(f"Attempting to add {username} to whitelist")
            self.rcon.connect()
            
            # Zuerst prüfen, ob der Spieler bereits auf der Whitelist steht
            whitelist_response = self.rcon.command("vpw list")
            logger.info(f"Current whitelist: {whitelist_response}")
            
            if username.lower() in whitelist_response.lower():
                logger.info(f"Player {username} is already on the whitelist")
                self.rcon.disconnect()
                return True
            
            # Direkter vpw-Befehl ohne Präfix
            response = self.rcon.command(f"vpw add {username}")
            logger.info(f"RCON response: {response}")
            
            # Wenn der Spieler offline ist und die UUID abgerufen wird, warten wir und prüfen dann die Whitelist
            if "player is offline, fetching uuid" in response.lower() or "fetching uuid from mojang" in response.lower():
                logger.info("Player is offline, fetching UUID. Waiting for the operation to complete...")
                
                # Nur 3 Versuche mit kürzeren Wartezeiten
                max_retries = 3
                wait_times = [5, 10, 10]  # Wartezeiten in Sekunden
                
                self.rcon.disconnect()
                
                for i in range(max_retries):
                    wait_time = wait_times[i]
                    logger.info(f"Waiting {wait_time} seconds before retry {i+1}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                    
                    # Erneut verbinden und prüfen
                    self.rcon.connect()
                    check_response = self.rcon.command("vpw list")
                    logger.info(f"Whitelist check attempt {i+1}: {check_response}")
                    
                    # Prüfe, ob der Spieler jetzt auf der Liste steht
                    if username.lower() in check_response.lower():
                        logger.info(f"Player {username} was successfully added to the whitelist on attempt {i+1}")
                        self.rcon.disconnect()
                        return True
                    
                    # Falls nicht, versuchen wir es erneut hinzuzufügen
                    if i < max_retries - 1:  # Beim letzten Versuch kein erneutes Hinzufügen
                        logger.info(f"Retry {i+1}: Attempting to add {username} again...")
                        retry_response = self.rcon.command(f"vpw add {username}")
                        logger.info(f"Retry {i+1} response: {retry_response}")
                    
                    self.rcon.disconnect()
                
                # Letzte Überprüfung
                self.rcon.connect()
                final_check = self.rcon.command("vpw list")
                logger.info(f"Final whitelist check after {max_retries} attempts: {final_check}")
                
                success = username.lower() in final_check.lower()
                logger.info(f"Final whitelist add result for {username}: {success}")
                
                self.rcon.disconnect()
                return success
            
            # Direkte Erfolgsantwort
            success_patterns = ["added", "added to whitelist"]
            direct_success = any(pattern in response.lower() for pattern in success_patterns)
            
            if direct_success:
                logger.info(f"Player {username} directly added to whitelist")
                return True
            
            # Prüfen, ob der Spieler trotz unklarer Antwort hinzugefügt wurde
            check_response = self.rcon.command("vpw list")
            if username.lower() in check_response.lower():
                logger.info(f"Player {username} is on the whitelist after command, despite unclear response")
                return True
            
            # Wenn wir hier ankommen, war die Operation wahrscheinlich nicht erfolgreich
            logger.warning(f"Whitelist add operation may have failed for {username}")
            return False
        except ConnectionRefusedError:
            logger.error("RCON connection refused. Is the Minecraft server running?")
            return False
        except TimeoutError:
            logger.error("RCON connection timed out. Is the server reachable?")
            return False
        except Exception as e:
            logger.error(f"RCON error: {str(e)}")
            return False
        finally:
            try:
                self.rcon.disconnect()
            except:
                pass
    
    async def whitelist_remove(self, username: str) -> bool:
        """Remove a player from the server whitelist."""
        try:
            logger.info(f"Attempting to remove {username} from whitelist")
            self.rcon.connect()
            
            # Zuerst prüfen, ob der Spieler auf der Whitelist steht
            whitelist_response = self.rcon.command("vpw list")
            logger.info(f"Current whitelist: {whitelist_response}")
            
            if username.lower() not in whitelist_response.lower():
                logger.info(f"Player {username} is not on the whitelist")
                self.rcon.disconnect()
                return True  # Bereits nicht auf der Liste = Erfolg
            
            # Direkter vpw-Befehl ohne Präfix
            response = self.rcon.command(f"vpw remove {username}")
            logger.info(f"RCON response: {response}")
            
            # Auf erfolgreiche Entfernung prüfen
            success_patterns = ["removed", "removed from whitelist"]
            direct_success = any(pattern in response.lower() for pattern in success_patterns)
            
            if direct_success:
                logger.info(f"Player {username} removed from whitelist")
                return True
            
            # Bei Unklarheit noch einmal die Whitelist prüfen
            check_response = self.rcon.command("vpw list")
            logger.info(f"Whitelist after remove attempt: {check_response}")
            
            # Prüfen, ob der Spieler jetzt von der Liste entfernt wurde
            success = username.lower() not in check_response.lower()
            logger.info(f"Whitelist remove result for {username}: {success}")
            
            return success
        except ConnectionRefusedError:
            logger.error("RCON connection refused. Is the Minecraft server running?")
            return False
        except TimeoutError:
            logger.error("RCON connection timed out. Is the server reachable?")
            return False
        except Exception as e:
            logger.error(f"RCON error: {str(e)}")
            return False
        finally:
            try:
                self.rcon.disconnect()
            except:
                pass

    async def whitelist_check(self, username: str) -> bool:
        """Check if a player is on the whitelist."""
        try:
            logger.info(f"Checking if {username} is on the whitelist")
            self.rcon.connect()
            
            # Whitelist abfragen
            whitelist_response = self.rcon.command("vpw list")
            logger.info(f"Current whitelist: {whitelist_response}")
            
            # Prüfen, ob der Spielername in der Antwort enthalten ist
            is_whitelisted = username.lower() in whitelist_response.lower()
            logger.info(f"Player {username} is {'on' if is_whitelisted else 'not on'} the whitelist")
            
            return is_whitelisted
        except Exception as e:
            logger.error(f"RCON error during whitelist check: {str(e)}")
            return False
        finally:
            try:
                self.rcon.disconnect()
            except:
                pass

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