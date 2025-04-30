import sqlite3
import logging
import time
import threading
from typing import Dict, List, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)

# Database connection with thread lock for safety
conn = sqlite3.connect("vk_bot.db", check_same_thread=False)
db_lock = threading.RLock()  # Reentrant lock for database operations
cursor = conn.cursor()

def init_db():
    # Initialize database tables if they don't exist.
    with db_lock:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            nickname TEXT,
            role TEXT DEFAULT 'user',  -- Оставляем для обратной совместимости
            messages_count INTEGER DEFAULT 0,
            warns INTEGER DEFAULT 0,
            mute_until INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT NULL,
            reg_date INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reason TEXT,
            timestamp INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            ban_timestamp INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        # Создаем таблицу для хранения ролей в конкретных беседах
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_roles (
            user_id INTEGER,
            peer_id INTEGER,
            role TEXT DEFAULT 'user',
            PRIMARY KEY (user_id, peer_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        logger.info("Database initialized successfully")

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    # Get user information from database.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Dictionary with user information or None if user doesn't exist
    with db_lock:
        cursor.execute("""
            SELECT 
            user_id, nickname, role, messages_count, warns, 
            mute_until, ban_reason, reg_date 
            FROM users 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
    if row:
        return {
            "user_id": row[0],
            "nickname": row[1],
            "role": row[2],
            "messages_count": row[3],
            "warns": row[4],
            "mute_until": row[5],
            "ban_reason": row[6],
            "reg_date": row[7]
        }
    return None

def add_user(user_id: int) -> None:
    # Add new user to database if not exists.
    #
    # Args:
    # user_id: VK user ID
    with db_lock:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, reg_date) VALUES (?, ?)",
            (user_id, int(time.time()))
        )
        conn.commit()

def update_message_count(user_id: int) -> None:
    # Increment user's message count.
    #
    # Args:
    # user_id: VK user ID
    with db_lock:
        cursor.execute("""
            INSERT INTO users (user_id, messages_count, reg_date) 
            VALUES (?, 1, ?) 
            ON CONFLICT(user_id) DO UPDATE SET 
            messages_count = messages_count + 1
        """, (user_id, int(time.time())))
        conn.commit()

def set_nickname(user_id: int, nickname: str) -> bool:
    # Set nickname for a user.
    #
    # Args:
    # user_id: VK user ID
    # nickname: New nickname
    #
    # Returns:
    # Success status
    with db_lock:
        cursor.execute("""
            UPDATE users 
            SET nickname = ? 
            WHERE user_id = ?
        """, (nickname, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        return success

def remove_nickname(user_id: int) -> bool:
    # Remove nickname from a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Success status
    with db_lock:
        cursor.execute("""
            UPDATE users 
            SET nickname = NULL 
            WHERE user_id = ?
        """, (user_id,))
        success = cursor.rowcount > 0
        conn.commit()
        return success

def find_user_by_nickname(nickname: str) -> List[Dict[str, Any]]:
    # Find users by nickname.
    #
    # Args:
    # nickname: Nickname to search for
    #
    # Returns:
    # List of matching users
    with db_lock:
        cursor.execute("""
            SELECT user_id, nickname, role 
            FROM users 
            WHERE nickname LIKE ?
        """, (f"%{nickname}%",))
        rows = cursor.fetchall()
    
    return [
        {"user_id": row[0], "nickname": row[1], "role": row[2]} 
        for row in rows
    ]

def get_users_with_nicknames() -> List[Dict[str, Any]]:
    # Get all users with nicknames.
    #
    # Returns:
    # List of users with nicknames
    with db_lock:
        cursor.execute("""
            SELECT user_id, nickname, role 
            FROM users 
            WHERE nickname IS NOT NULL
        """)
        rows = cursor.fetchall()
    
    return [
        {"user_id": row[0], "nickname": row[1], "role": row[2]} 
        for row in rows
    ]

def get_users_without_nicknames() -> List[Dict[str, Any]]:
    # Get all users without nicknames.
    #
    # Returns:
    # List of users without nicknames
    with db_lock:
        cursor.execute("""
            SELECT user_id, role 
            FROM users 
            WHERE nickname IS NULL
        """)
        rows = cursor.fetchall()
    
    return [
        {"user_id": row[0], "role": row[1]} 
        for row in rows
    ]

def add_warn(user_id: int, reason: str) -> int:
    # Add warning to a user.
    #
    # Args:
    # user_id: VK user ID
    # reason: Warning reason
    #
    # Returns:
    # New warn count
    timestamp = int(time.time())
    with db_lock:
        # Add warn record
        cursor.execute("""
            INSERT INTO warns (user_id, reason, timestamp) 
            VALUES (?, ?, ?)
        """, (user_id, reason, timestamp))
        
        # Update warn count
        cursor.execute("""
            UPDATE users 
            SET warns = warns + 1 
            WHERE user_id = ?
        """, (user_id,))
        
        # Get new warn count
        cursor.execute(
            "SELECT warns FROM users WHERE user_id = ?",
            (user_id,)
        )
        warn_count = cursor.fetchone()[0]
        
        conn.commit()
        return warn_count

def remove_warn(user_id: int) -> int:
    # Remove a warning from a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # New warn count
    with db_lock:
        # Get the most recent warning
        cursor.execute("""
            SELECT id FROM warns 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return 0
        
        warn_id = row[0]
        
        # Delete the warning
        cursor.execute(
            "DELETE FROM warns WHERE id = ?",
            (warn_id,)
        )
        
        # Update warn count
        cursor.execute("""
            UPDATE users 
            SET warns = MAX(0, warns - 1) 
            WHERE user_id = ?
        """, (user_id,))
        
        # Get new warn count
        cursor.execute(
            "SELECT warns FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        warn_count = row[0] if row else 0
        
        conn.commit()
        return warn_count

def get_warns(user_id: int) -> int:
    # Get warning count for a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Warning count
    with db_lock:
        cursor.execute(
            "SELECT warns FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
    
    return row[0] if row else 0

def get_warn_history(user_id: int) -> List[Dict[str, Any]]:
    # Get warning history for a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # List of warnings
    with db_lock:
        cursor.execute("""
            SELECT id, reason, timestamp 
            FROM warns 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        """, (user_id,))
        rows = cursor.fetchall()
    
    return [
        {"id": row[0], "reason": row[1], "timestamp": row[2]} 
        for row in rows
    ]

def get_all_warns() -> List[Dict[str, Any]]:
    # Get all warnings.
    #
    # Returns:
    # List of all warnings
    with db_lock:
        cursor.execute("""
            SELECT w.id, w.user_id, u.nickname, w.reason, w.timestamp 
            FROM warns w
            JOIN users u ON w.user_id = u.user_id
            ORDER BY w.timestamp DESC
        """)
        rows = cursor.fetchall()
    
    return [
        {
            "id": row[0], 
            "user_id": row[1], 
            "nickname": row[2], 
            "reason": row[3], 
            "timestamp": row[4]
        } 
        for row in rows
    ]

def set_mute(user_id: int, duration: int, reason: str) -> int:
    # Mute a user.
    #
    # Args:
    # user_id: VK user ID
    # duration: Mute duration in seconds
    # reason: Mute reason
    #
    # Returns:
    # Mute end timestamp
    mute_until = int(time.time()) + duration
    with db_lock:
        cursor.execute("""
            UPDATE users 
            SET mute_until = ? 
            WHERE user_id = ?
        """, (mute_until, user_id))
        conn.commit()
        return mute_until

def remove_mute(user_id: int) -> bool:
    # Remove mute from a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Success status
    with db_lock:
        cursor.execute("""
            UPDATE users 
            SET mute_until = 0 
            WHERE user_id = ?
        """, (user_id,))
        success = cursor.rowcount > 0
        conn.commit()
        return success

def get_mute(user_id: int) -> int:
    # Get remaining mute time for a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Mute end timestamp
    with db_lock:
        cursor.execute(
            "SELECT mute_until FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
    
    return row[0] if row else 0

def get_muted_users() -> List[Dict[str, Any]]:
    # Get all muted users.
    #
    # Returns:
    # List of muted users
    current_time = int(time.time())
    with db_lock:
        cursor.execute("""
            SELECT user_id, nickname, mute_until 
            FROM users 
            WHERE mute_until > ?
            ORDER BY mute_until DESC
        """, (current_time,))
        rows = cursor.fetchall()
    
    return [
        {
            "user_id": row[0], 
            "nickname": row[1], 
            "mute_until": row[2]
        } 
        for row in rows
    ]

def ban_user(user_id: int, reason: str) -> bool:
    # Ban a user.
    #
    # Args:
    # user_id: VK user ID
    # reason: Ban reason
    #
    # Returns:
    # Success status
    ban_timestamp = int(time.time())
    with db_lock:
        cursor.execute("""
            INSERT OR REPLACE INTO bans (user_id, reason, ban_timestamp) 
            VALUES (?, ?, ?)
        """, (user_id, reason, ban_timestamp))
        conn.commit()
        return True

def unban_user(user_id: int) -> bool:
    # Unban a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Success status
    with db_lock:
        cursor.execute(
            "DELETE FROM bans WHERE user_id = ?",
            (user_id,)
        )
        success = cursor.rowcount > 0
        conn.commit()
        return success

def get_ban(user_id: int) -> Optional[Dict[str, Any]]:
    # Get ban information for a user.
    #
    # Args:
    # user_id: VK user ID
    #
    # Returns:
    # Ban information or None if user is not banned
    with db_lock:
        cursor.execute("""
            SELECT reason, ban_timestamp 
            FROM bans 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
    
    if row:
        return {
            "reason": row[0],
            "ban_timestamp": row[1]
        }
    return None

def get_banned_users() -> List[Dict[str, Any]]:
    # Get all banned users.
    #
    # Returns:
    # List of banned users
    with db_lock:
        cursor.execute("""
            SELECT b.user_id, u.nickname, b.reason, b.ban_timestamp 
            FROM bans b
            LEFT JOIN users u ON b.user_id = u.user_id
            ORDER BY b.ban_timestamp DESC
        """)
        rows = cursor.fetchall()
    
    return [
        {
            "user_id": row[0], 
            "nickname": row[1], 
            "reason": row[2], 
            "ban_timestamp": row[3]
        } 
        for row in rows
    ]

def set_role(user_id: int, role: str, peer_id: Optional[int] = None) -> bool:
    # Set role for a user.
    #
    # Args:
    # user_id: VK user ID
    # role: Role name
    # peer_id: Optional conversation ID
    #
    # Returns:
    # Success status
    with db_lock:
        if peer_id:
            # Set role for specific conversation
            cursor.execute("""
                INSERT INTO conversation_roles (user_id, peer_id, role) 
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, peer_id) DO UPDATE SET role = ?
            """, (user_id, peer_id, role, role))
        else:
            # Set global role
            cursor.execute("""
                UPDATE users
                SET role = ?
                WHERE user_id = ?
            """, (role, user_id))
            
        success = cursor.rowcount > 0
        conn.commit()
        return success

def get_role(user_id: int, peer_id: Optional[int] = None) -> str:
    # Get role for a user.
    #
    # Args:
    # user_id: VK user ID
    # peer_id: Optional conversation ID
    #
    # Returns:
    # User role
    with db_lock:
        # If peer_id is specified, try to get conversation-specific role
        if peer_id:
            cursor.execute("""
                SELECT role FROM conversation_roles 
                WHERE user_id = ? AND peer_id = ?
            """, (user_id, peer_id))
            row = cursor.fetchone()
            
            # If found, return it
            if row:
                return row[0]
        
        # Otherwise, get global role
        cursor.execute("""
            SELECT role FROM users 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
    return row[0] if row else "user"

def get_staff(peer_id: Optional[int] = None) -> List[Dict[str, Any]]:
    # Get staff members.
    #
    # Args:
    # peer_id: Optional conversation ID to filter roles by conversation
    #
    # Returns:
    # List of staff members
    with db_lock:
        if peer_id:
            # Get roles specific to the conversation
            cursor.execute("""
                SELECT cr.user_id, u.nickname, cr.role
                FROM conversation_roles cr
                LEFT JOIN users u ON cr.user_id = u.user_id
                WHERE cr.peer_id = ? AND cr.role != 'user'
                ORDER BY 
                CASE cr.role 
                    WHEN 'creator' THEN 5
                    WHEN 'admin' THEN 4
                    WHEN 'senior_moderator' THEN 3
                    WHEN 'moderator' THEN 2
                    ELSE 1
                END DESC
            """, (peer_id,))
        else:
            # Get all global roles
            cursor.execute("""
                SELECT user_id, nickname, role
                FROM users
                WHERE role != 'user'
                ORDER BY 
                CASE role 
                    WHEN 'creator' THEN 5
                    WHEN 'admin' THEN 4
                    WHEN 'senior_moderator' THEN 3
                    WHEN 'moderator' THEN 2
                    ELSE 1
                END DESC
            """)
            
        rows = cursor.fetchall()
    
    return [
        {"user_id": row[0], "nickname": row[1], "role": row[2]} 
        for row in rows
    ]

def get_inactive_users(threshold_days: int = 30) -> List[Dict[str, Any]]:
    # Get inactive users.
    #
    # Args:
    # threshold_days: Number of days without activity to consider a user inactive
    #
    # Returns:
    # List of inactive users
    threshold_timestamp = int(time.time()) - (threshold_days * 86400)
    with db_lock:
        cursor.execute("""
            SELECT user_id, nickname, messages_count, role
            FROM users
            WHERE reg_date < ? AND messages_count < 5
            ORDER BY reg_date ASC
        """, (threshold_timestamp,))
        rows = cursor.fetchall()
    
    return [
        {
            "user_id": row[0], 
            "nickname": row[1], 
            "messages_count": row[2],
            "role": row[3]
        } 
        for row in rows
    ]