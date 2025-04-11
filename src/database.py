"""
Database configuration and models for the QuingCraft bot.
"""
from typing import Optional
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
    
    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS whitelist_requests (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT NOT NULL,
                    minecraft_username VARCHAR(16) NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(discord_id, status)
                )
            """)
            self.conn.commit()
    
    def add_whitelist_request(self, discord_id: int, minecraft_username: str) -> bool:
        """Add a new whitelist request to the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO whitelist_requests (discord_id, minecraft_username, status)
                    VALUES (%s, %s, 'pending')
                    ON CONFLICT (discord_id, status) DO NOTHING
                    RETURNING id
                """, (discord_id, minecraft_username))
                self.conn.commit()
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    def get_pending_request(self, discord_id: int) -> Optional[dict]:
        """Get a pending whitelist request for a user."""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM whitelist_requests
                    WHERE discord_id = %s AND status = 'pending'
                """, (discord_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Database error: {e}")
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
            print(f"Database error: {e}")
            return False
    
    def approve_request(self, discord_id: int) -> bool:
        """Approve a whitelist request."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE whitelist_requests
                    SET status = 'approved'
                    WHERE discord_id = %s AND status = 'pending'
                    RETURNING id
                """, (discord_id,))
                self.conn.commit()
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Database error: {e}")
            return False

    def reject_request(self, discord_id: int) -> bool:
        """Reject a whitelist request."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE whitelist_requests
                    SET status = 'rejected'
                    WHERE discord_id = %s AND status = 'pending'
                    RETURNING id
                """, (discord_id,))
                self.conn.commit()
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close() 