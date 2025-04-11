"""
Database configuration and models for the QuingCraft bot.
"""
from typing import Optional, Tuple
import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

class Database:
    """Handles database operations for the QuingCraft bot."""
    
    def __init__(self) -> None:
        """Initialize database connection."""
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        self._create_tables()
        self._update_schema()
    
    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS whitelist_requests (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT NOT NULL,
                    minecraft_username VARCHAR(16) NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
    
    def _update_schema(self) -> None:
        """Update database schema if needed."""
        try:
            # Entfernen der Unique Constraint, falls vorhanden
            with self.conn.cursor() as cur:
                # Prüfen, ob die Constraint existiert
                cur.execute("""
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'whitelist_requests_discord_id_status_key'
                """)
                if cur.fetchone():
                    # Constraint existiert, entfernen
                    cur.execute("""
                        ALTER TABLE whitelist_requests
                        DROP CONSTRAINT whitelist_requests_discord_id_status_key
                    """)
                    print("Removed unique constraint on discord_id and status")
                
                # Entfernen der potenziell problematischen unique index auf minecraft_username
                cur.execute("""
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'whitelist_requests_minecraft_username_unique_status'
                """)
                if cur.fetchone():
                    cur.execute("""
                        DROP INDEX IF EXISTS whitelist_requests_minecraft_username_unique_status
                    """)
                    print("Removed unique index on minecraft_username and status")
                
                self.conn.commit()
                print("Updated database schema successfully")
        except Exception as e:
            print(f"Error updating schema: {e}")
            self.conn.rollback()
    
    def add_whitelist_request(self, discord_id: int, minecraft_username: str) -> bool:
        """Add a new whitelist request to the database."""
        try:
            with self.conn.cursor() as cur:
                # Prüfen, ob der Spieler bereits auf der Whitelist steht (approved status)
                cur.execute("""
                    SELECT discord_id FROM whitelist_requests
                    WHERE minecraft_username = %s AND status = 'approved'
                """, (minecraft_username,))
                existing = cur.fetchone()
                if existing:
                    print(f"Player {minecraft_username} already on whitelist")
                    
                    # Wenn der Antrag von demselben Discord-Benutzer stammt, geben wir true zurück
                    if existing[0] == discord_id:
                        print(f"This is the user's own approved request")
                        return True
                    return False
                
                # Prüfen, ob ein ausstehender Antrag für diesen Benutzer existiert
                cur.execute("""
                    SELECT minecraft_username FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                existing_request = cur.fetchone()
                if existing_request:
                    print(f"User {discord_id} already has a pending request for {existing_request[0]}")
                    
                    # Wenn der Benutzer für denselben Minecraft-Namen einen Antrag hat, geben wir true zurück
                    if existing_request[0] == minecraft_username:
                        print(f"This is the same request, returning success")
                        return True
                    return False
                
                # Prüfen, ob ein ausstehender Antrag für diesen Minecraft-Namen existiert
                cur.execute("""
                    SELECT discord_id FROM whitelist_requests
                    WHERE minecraft_username = %s AND status = 'pending'
                """, (minecraft_username,))
                existing_name_request = cur.fetchone()
                if existing_name_request and existing_name_request[0] != discord_id:
                    print(f"Player name {minecraft_username} already has a pending request from another user")
                    return False
                
                # Neuen Antrag hinzufügen
                cur.execute("""
                    INSERT INTO whitelist_requests (discord_id, minecraft_username, status)
                    VALUES (%s, %s, 'pending')
                    RETURNING id
                """, (discord_id, minecraft_username))
                self.conn.commit()
                result = cur.fetchone()
                return result is not None
        except Exception as e:
            print(f"Database error in add_whitelist_request: {e}")
            self.conn.rollback()
            return False
    
    def get_pending_request(self, discord_id: int) -> Optional[tuple]:
        """Get a pending whitelist request for a user."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Database error in get_pending_request: {e}")
            self.conn.rollback()
            return None
    
    def update_request_status(self, request_id: int, status: str) -> bool:
        """Update the status of a whitelist request."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE whitelist_requests
                    SET status = %s
                    WHERE id = %s
                """, (status, request_id))
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Database error in update_request_status: {e}")
            self.conn.rollback()
            return False
    
    def approve_request(self, discord_id: int) -> Tuple[bool, Optional[str]]:
        """Approve a whitelist request. Returns (success, minecraft_username)."""
        try:
            with self.conn.cursor() as cur:
                # Holen des ausstehenden Antrags
                cur.execute("""
                    SELECT id, minecraft_username FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                request = cur.fetchone()
                
                if not request:
                    print(f"No pending request found for user {discord_id}")
                    return False, None
                
                request_id, minecraft_username = request
                
                # Prüfen, ob der Minecraft-Name bereits auf der Whitelist steht
                cur.execute("""
                    SELECT id FROM whitelist_requests
                    WHERE minecraft_username = %s AND status = 'approved' AND id != %s
                """, (minecraft_username, request_id))
                
                if cur.fetchone():
                    # Name ist bereits auf der Whitelist, setzen wir diesen Antrag auf "duplicate"
                    cur.execute("""
                        UPDATE whitelist_requests
                        SET status = 'duplicate'
                        WHERE id = %s
                    """, (request_id,))
                    self.conn.commit()
                    print(f"Set request to duplicate for {minecraft_username}")
                    return True, minecraft_username
                
                # Aktualisieren des Status auf "approved"
                cur.execute("""
                    UPDATE whitelist_requests
                    SET status = 'approved'
                    WHERE id = %s
                """, (request_id,))
                self.conn.commit()
                print(f"Approved request for {minecraft_username}")
                return True, minecraft_username
        except Exception as e:
            print(f"Database error in approve_request: {e}")
            self.conn.rollback()
            return False, None

    def reject_request(self, discord_id: int) -> Tuple[bool, Optional[str]]:
        """Reject a whitelist request. Returns (success, minecraft_username)."""
        try:
            with self.conn.cursor() as cur:
                # Holen der ID des ausstehenden Antrags
                cur.execute("""
                    SELECT id, minecraft_username FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                request = cur.fetchone()
                
                if not request:
                    print(f"No pending request found for user {discord_id}")
                    return False, None
                
                request_id, minecraft_username = request
                
                cur.execute("""
                    UPDATE whitelist_requests
                    SET status = 'rejected'
                    WHERE id = %s
                """, (request_id,))
                self.conn.commit()
                print(f"Rejected request ID {request_id} for {minecraft_username}")
                return True, minecraft_username
        except Exception as e:
            print(f"Database error in reject_request: {e}")
            self.conn.rollback()
            return False, None
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close() 