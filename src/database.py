"""
Database configuration and models for the QuingCraft bot.
"""
from typing import Optional, Tuple, List
import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

class Database:
    """Handles database operations for the QuingCraft bot."""
    
    def __init__(self) -> None:
        """Initialize database connection."""
        # Debug: Show all environment variables
        print("DEBUG: Environment variables:")
        for key in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]:
            value = os.getenv(key)
            if value:
                print(f"DEBUG: {key} is set")
            else:
                print(f"DEBUG: {key} is not set!")
        
        # Connect to database
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
            # Whitelist requests table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS whitelist_requests (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT NOT NULL,
                    minecraft_username VARCHAR(16) NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    approved_by BIGINT,
                    rejected_by BIGINT,
                    processed_at TIMESTAMP,
                    message_id BIGINT
                )
            """)
            
            # Role requests table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS role_requests (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT NOT NULL,
                    minecraft_username VARCHAR(16) NOT NULL,
                    requested_role VARCHAR(32) NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    approved_by BIGINT,
                    rejected_by BIGINT,
                    processed_at TIMESTAMP,
                    message_id BIGINT
                )
            """)
            
            self.conn.commit()
    
    def _update_schema(self) -> None:
        """Update database schema if needed."""
        try:
            # Update whitelist_requests schema
            with self.conn.cursor() as cur:
                # Check if constraint exists
                cur.execute("""
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'whitelist_requests_discord_id_status_key'
                """)
                if cur.fetchone():
                    # Constraint exists, remove it
                    cur.execute("""
                        ALTER TABLE whitelist_requests
                        DROP CONSTRAINT whitelist_requests_discord_id_status_key
                    """)
                    print("Removed unique constraint on discord_id and status")
                
                # Check if new columns already exist
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'whitelist_requests' AND column_name = 'reason'
                """)
                if not cur.fetchone():
                    # Add columns if they don't exist
                    cur.execute("""
                        ALTER TABLE whitelist_requests
                        ADD COLUMN reason TEXT,
                        ADD COLUMN approved_by BIGINT,
                        ADD COLUMN rejected_by BIGINT,
                        ADD COLUMN processed_at TIMESTAMP
                    """)
                    print("Added new columns to whitelist_requests table")
                
                # Check if message_id column exists
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'whitelist_requests' AND column_name = 'message_id'
                """)
                if not cur.fetchone():
                    # Add message_id column
                    cur.execute("""
                        ALTER TABLE whitelist_requests
                        ADD COLUMN message_id BIGINT
                    """)
                    print("Added message_id column to whitelist_requests table")
                
                # Remove potentially problematic unique index on minecraft_username
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
    
    def add_whitelist_request(self, discord_id: int, minecraft_username: str, reason: str = None, message_id: int = None) -> bool:
        """Add a new whitelist request to the database."""
        try:
            with self.conn.cursor() as cur:
                # First check if there's already a pending request from this user
                cur.execute("""
                    SELECT minecraft_username FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                existing_request = cur.fetchone()
                if existing_request:
                    print(f"User {discord_id} already has a pending request for {existing_request[0]}")
                    
                    # If the user has a request for the same Minecraft name, return true
                    if existing_request[0] == minecraft_username:
                        print(f"This is the same request, returning success")
                        # Update message_id if provided
                        if message_id:
                            cur.execute("""
                                UPDATE whitelist_requests 
                                SET message_id = %s
                                WHERE discord_id = %s AND status = 'pending'
                            """, (message_id, discord_id))
                            self.conn.commit()
                        return True
                    return False
                
                # Check if another user has a pending request for this Minecraft username
                cur.execute("""
                    SELECT discord_id FROM whitelist_requests
                    WHERE minecraft_username = %s AND status = 'pending'
                """, (minecraft_username,))
                existing_name_request = cur.fetchone()
                if existing_name_request and existing_name_request[0] != discord_id:
                    print(f"Player name {minecraft_username} already has a pending request from another user")
                    return False
                
                # Check if this user had an approved request for this username before
                # Instead of blocking the request, we'll check if they're actually on the whitelist
                cur.execute("""
                    SELECT discord_id, id FROM whitelist_requests
                    WHERE minecraft_username = %s AND discord_id = %s AND status = 'approved'
                    ORDER BY processed_at DESC
                    LIMIT 1
                """, (minecraft_username, discord_id))
                previously_approved = cur.fetchone()
                
                if previously_approved:
                    print(f"User {discord_id} previously had an approved request for {minecraft_username}")
                    # We'll mark the old request as 'removed' so we know they were once approved
                    cur.execute("""
                        UPDATE whitelist_requests
                        SET status = 'removed'
                        WHERE id = %s
                    """, (previously_approved[1],))
                    print(f"Marked previous request as 'removed'")
                
                # Add new request
                cur.execute("""
                    INSERT INTO whitelist_requests (discord_id, minecraft_username, status, reason, message_id)
                    VALUES (%s, %s, 'pending', %s, %s)
                    RETURNING id
                """, (discord_id, minecraft_username, reason, message_id))
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
    
    def update_request_status(self, request_id: int, status: str, moderator_id: int = None) -> bool:
        """Update the status of a whitelist request."""
        try:
            with self.conn.cursor() as cur:
                # Je nach Status den entsprechenden Moderator setzen
                if status == 'approved':
                    cur.execute("""
                        UPDATE whitelist_requests
                        SET status = %s, approved_by = %s, processed_at = NOW()
                        WHERE id = %s
                    """, (status, moderator_id, request_id))
                elif status == 'rejected':
                    cur.execute("""
                        UPDATE whitelist_requests
                        SET status = %s, rejected_by = %s, processed_at = NOW()
                        WHERE id = %s
                    """, (status, moderator_id, request_id))
                else:
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
    
    def approve_request(self, discord_id: int, moderator_id: int = None) -> Tuple[bool, Optional[str]]:
        """Approve a whitelist request for a user."""
        try:
            with self.conn.cursor() as cur:
                # Check if the Minecraft name is already on the whitelist
                cur.execute("""
                    SELECT id, minecraft_username FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (discord_id,))
                request = cur.fetchone()
                
                if not request:
                    print(f"No pending request found for user {discord_id}")
                    return False, None
                
                request_id, minecraft_username = request
                
                # Update the request status
                cur.execute("""
                    UPDATE whitelist_requests 
                    SET status = 'approved', approved_by = %s, processed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (moderator_id, request_id))
                
                # Get the message ID for this request to update the message
                cur.execute("""
                    SELECT message_id FROM whitelist_requests
                    WHERE id = %s
                """, (request_id,))
                message_id_row = cur.fetchone()
                message_id = message_id_row[0] if message_id_row else None
                
                self.conn.commit()
                print(f"Approved whitelist request for {minecraft_username} (Discord ID: {discord_id})")
                return True, minecraft_username
        except Exception as e:
            print(f"Error approving whitelist request: {e}")
            self.conn.rollback()
            return False, None

    def reject_request(self, discord_id: int, moderator_id: int = None) -> Tuple[bool, Optional[str]]:
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
                    SET status = 'rejected', rejected_by = %s, processed_at = NOW()
                    WHERE id = %s
                """, (moderator_id, request_id))
                self.conn.commit()
                print(f"Rejected request ID {request_id} for {minecraft_username}")
                return True, minecraft_username
        except Exception as e:
            print(f"Database error in reject_request: {e}")
            self.conn.rollback()
            return False, None
    
    def get_all_pending_requests(self) -> List[tuple]:
        """Get all pending whitelist requests."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM whitelist_requests
                    WHERE status = 'pending'
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Database error in get_all_pending_requests: {e}")
            self.conn.rollback()
            return []
    
    def get_request_by_minecraft_username(self, minecraft_username: str) -> Optional[tuple]:
        """Get a request by Minecraft username."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM whitelist_requests
                    WHERE minecraft_username = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (minecraft_username,))
                return cur.fetchone()
        except Exception as e:
            print(f"Database error in get_request_by_minecraft_username: {e}")
            self.conn.rollback()
            return None
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    # Füge neue Methoden für Rollenanfragen hinzu
    def add_role_request(self, discord_id: int, minecraft_username: str, requested_role: str, reason: str = None, message_id: int = None) -> bool:
        """Add a new role request to the database."""
        try:
            with self.conn.cursor() as cur:
                # Check if a pending request exists for this user
                cur.execute("""
                    SELECT minecraft_username, requested_role FROM role_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                existing_request = cur.fetchone()
                if existing_request:
                    print(f"User {discord_id} already has a pending role request for {existing_request[0]}")
                    return False
                
                # Add new request
                cur.execute("""
                    INSERT INTO role_requests (discord_id, minecraft_username, requested_role, status, reason, message_id)
                    VALUES (%s, %s, %s, 'pending', %s, %s)
                    RETURNING id
                """, (discord_id, minecraft_username, requested_role, reason, message_id))
                self.conn.commit()
                result = cur.fetchone()
                return result is not None
        except Exception as e:
            print(f"Error adding role request: {e}")
            self.conn.rollback()
            return False
    
    def get_pending_role_request(self, discord_id: int) -> Optional[tuple]:
        """Get a pending role request for a user."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM role_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Database error in get_pending_role_request: {e}")
            self.conn.rollback()
            return None
    
    def get_all_pending_role_requests(self) -> List[tuple]:
        """Get all pending role requests."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM role_requests
                    WHERE status = 'pending'
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Database error in get_all_pending_role_requests: {e}")
            self.conn.rollback()
            return []
    
    def update_role_request_status(self, request_id: int, status: str, moderator_id: int = None) -> bool:
        """Update the status of a role request."""
        try:
            with self.conn.cursor() as cur:
                if status == 'approved':
                    cur.execute("""
                        UPDATE role_requests
                        SET status = %s, approved_by = %s, processed_at = NOW()
                        WHERE id = %s
                    """, (status, moderator_id, request_id))
                elif status == 'rejected':
                    cur.execute("""
                        UPDATE role_requests
                        SET status = %s, rejected_by = %s, processed_at = NOW()
                        WHERE id = %s
                    """, (status, moderator_id, request_id))
                else:
                    cur.execute("""
                        UPDATE role_requests
                        SET status = %s
                        WHERE id = %s
                    """, (status, request_id))
                
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Database error in update_role_request_status: {e}")
            self.conn.rollback()
            return False
    
    def set_whitelist_request_message_id(self, discord_id: int, message_id: int) -> bool:
        """Update the message ID for a pending whitelist request."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE whitelist_requests
                    SET message_id = %s
                    WHERE discord_id = %s AND status = 'pending'
                """, (message_id, discord_id))
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Database error in set_whitelist_request_message_id: {e}")
            self.conn.rollback()
            return False
            
    def update_role_request_message_id(self, discord_id: int, message_id: int) -> bool:
        """Update the message ID for a pending role request."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE role_requests
                    SET message_id = %s
                    WHERE discord_id = %s AND status = 'pending'
                """, (message_id, discord_id))
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Database error in update_role_request_message_id: {e}")
            self.conn.rollback()
            return False
    
    def get_whitelist_users(self) -> List[tuple]:
        """Get list of approved whitelist users."""
        try:
            with self.conn.cursor() as cur:
                # Check if this user is already in the approved users
                cur.execute("""
                    SELECT discord_id, minecraft_username, created_at, processed_at
                    FROM whitelist_requests
                    WHERE status = 'approved'
                    ORDER BY processed_at DESC
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Error getting whitelist users: {e}")
            return [] 