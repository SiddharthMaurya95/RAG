import sqlite3
from core.paths import get_db_path

def migrate_db_for_sessions(db_path="data/automotive.db"):
    """
    Ensures that the chat_sessions table exists and the chat_history table
    has a session_id column, mapping existing history to a default session.
    """
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Create chat_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        # Check if chat_history has session_id column
        cursor.execute("PRAGMA table_info(chat_history);")
        columns = [row[1] for row in cursor.fetchall()]
        if "session_id" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN session_id INTEGER;")
            conn.commit()
            
            # Map existing chat history messages to a default session for each user
            cursor.execute("SELECT DISTINCT user_id FROM chat_history;")
            users_with_history = [row[0] for row in cursor.fetchall()]
            for uid in users_with_history:
                cursor.execute(
                    "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?);",
                    (uid, "Initial Chat")
                )
                session_id = cursor.lastrowid
                cursor.execute(
                    "UPDATE chat_history SET session_id = ? WHERE user_id = ? AND session_id IS NULL;",
                    (session_id, uid)
                )
            conn.commit()
    except Exception as e:
        print(f"Error migrating DB for sessions: {e}")
    finally:
        conn.close()

def verify_or_create_user(username, db_path="data/automotive.db"):
    """
    Checks if a username exists in the users table.
    If it does, returns its user_id.
    If it does not, inserts it and returns the newly generated user_id.
    """
    db_path = get_db_path(db_path)
    migrate_db_for_sessions(db_path)
    cleaned_username = str(username).strip()
    if not cleaned_username:
        return None
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = ?;", (cleaned_username,))
        row = cursor.fetchone()
        
        if row:
            user_id = row[0]
            print(f"User '{cleaned_username}' logged in (ID: {user_id}).")
        else:
            # Create user
            cursor.execute("INSERT INTO users (username) VALUES (?);", (cleaned_username,))
            conn.commit()
            user_id = cursor.lastrowid
            print(f"Created new user '{cleaned_username}' (ID: {user_id}).")
            
        return user_id
    except Exception as e:
        print(f"Error verifying user: {e}")
        return None
    finally:
        conn.close()

def create_chat_session(user_id, title="New Chat", db_path="data/automotive.db"):
    """Creates a new chat session for a user and returns its ID."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?);",
            (user_id, title)
        )
        conn.commit()
        session_id = cursor.lastrowid
        return session_id
    except Exception as e:
        print(f"Error creating chat session: {e}")
        return None
    finally:
        conn.close()

def get_user_chat_sessions(user_id, db_path="data/automotive.db"):
    """Loads all chat sessions for a specific user ID."""
    db_path = get_db_path(db_path)
    migrate_db_for_sessions(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, created_at 
        FROM chat_sessions 
        WHERE user_id = ? 
        ORDER BY created_at DESC;
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    sessions = []
    for row in rows:
        sessions.append({
            "id": row[0],
            "title": row[1],
            "created_at": row[2]
        })
    return sessions

def get_session_chat_history(user_id, session_id, db_path="data/automotive.db", limit=100):
    """Loads previous chat history for a specific session ID."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content 
        FROM chat_history 
        WHERE user_id = ? AND session_id = ? 
        ORDER BY timestamp ASC 
        LIMIT ?;
    """, (user_id, session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for role, content in rows:
        history.append({"role": role, "content": content})
    return history

def update_chat_session_title(session_id, title, db_path="data/automotive.db"):
    """Updates the title of a specific chat session."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE chat_sessions SET title = ? WHERE id = ?;",
            (title, session_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error updating chat session title: {e}")
    finally:
        conn.close()

def delete_chat_session(session_id, db_path="data/automotive.db"):
    """Deletes a specific chat session and all its associated chat history."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM chat_history WHERE session_id = ?;", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?;", (session_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting chat session: {e}")
    finally:
        conn.close()

def add_chat_message(user_id, session_id, role, content, db_path="data/automotive.db"):
    """Saves a new chat message to the database under a session."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO chat_history (user_id, session_id, role, content)
            VALUES (?, ?, ?, ?);
        """, (user_id, session_id, role, content))
        conn.commit()
    except Exception as e:
        print(f"Error saving chat message: {e}")
    finally:
        conn.close()

def get_user_chat_history(user_id, db_path="data/automotive.db", limit=50):
    """Fallback function for loading chat history globally or for the first session."""
    db_path = get_db_path(db_path)
    migrate_db_for_sessions(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM chat_sessions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1;
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        session_id = row[0]
        conn.close()
        return get_session_chat_history(user_id, session_id, db_path, limit)
    
    cursor.execute("""
        SELECT role, content 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp ASC 
        LIMIT ?;
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in rows]


