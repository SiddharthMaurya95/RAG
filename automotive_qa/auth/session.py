import datetime
from core.database import Base, get_engine, get_session, User, ChatSession, ChatHistory

def migrate_db_for_sessions(db_path="data/automotive.db"):
    """
    Ensures that the database tables and schema exist by calling Base.metadata.create_all().
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

def verify_or_create_user(username, db_path="data/automotive.db"):
    """
    Checks if a username exists in the users table.
    If it does, returns its user_id.
    If it does not, inserts it and returns the newly generated user_id.
    """
    migrate_db_for_sessions(db_path)
    cleaned_username = str(username).strip()
    if not cleaned_username:
        return None
        
    session = get_session(db_path)
    try:
        user = session.query(User).filter(User.username == cleaned_username).first()
        if user:
            user_id = user.id
            print(f"User '{cleaned_username}' logged in (ID: {user_id}).")
        else:
            user = User(username=cleaned_username)
            session.add(user)
            session.commit()
            user_id = user.id
            print(f"Created new user '{cleaned_username}' (ID: {user_id}).")
        return user_id
    except Exception as e:
        session.rollback()
        print(f"Error verifying user: {e}")
        return None
    finally:
        session.close()

def create_chat_session(user_id, title="New Chat", db_path="data/automotive.db"):
    """Creates a new chat session for a user and returns its ID."""
    session = get_session(db_path)
    try:
        chat_sess = ChatSession(user_id=user_id, title=title)
        session.add(chat_sess)
        session.commit()
        return chat_sess.id
    except Exception as e:
        session.rollback()
        print(f"Error creating chat session: {e}")
        return None
    finally:
        session.close()

def get_user_chat_sessions(user_id, db_path="data/automotive.db"):
    """Loads all chat sessions for a specific user ID."""
    migrate_db_for_sessions(db_path)
    session = get_session(db_path)
    try:
        rows = session.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
        sessions = []
        for r in rows:
            created_at_val = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.created_at, datetime.datetime) else str(r.created_at)
            sessions.append({
                "id": r.id,
                "title": r.title,
                "created_at": created_at_val
            })
        return sessions
    finally:
        session.close()

def get_session_chat_history(user_id, session_id, db_path="data/automotive.db", limit=100):
    """Loads previous chat history for a specific session ID."""
    session = get_session(db_path)
    try:
        rows = session.query(ChatHistory).filter(
            ChatHistory.user_id == user_id, 
            ChatHistory.session_id == session_id
        ).order_by(ChatHistory.timestamp.asc()).limit(limit).all()
        
        history = []
        for r in rows:
            history.append({"id": r.id, "role": r.role, "content": r.content, "intent": r.intent})
        return history
    finally:
        session.close()

def delete_chat_message(message_id, db_path="data/automotive.db"):
    """Deletes a specific chat message by its ID."""
    session = get_session(db_path)
    try:
        msg = session.query(ChatHistory).filter(ChatHistory.id == message_id).first()
        if msg:
            session.delete(msg)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error deleting chat message: {e}")
    finally:
        session.close()

def update_chat_session_title(session_id, title, db_path="data/automotive.db"):
    """Updates the title of a specific chat session."""
    session = get_session(db_path)
    try:
        session.query(ChatSession).filter(ChatSession.id == session_id).update({
            ChatSession.title: title
        })
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error updating chat session title: {e}")
    finally:
        session.close()

def delete_chat_session(session_id, db_path="data/automotive.db"):
    """Deletes a specific chat session, all its associated chat history, and any associated query caches."""
    import hashlib
    from core.database import QueryCache as DBQueryCache
    session = get_session(db_path)
    try:
        # Retrieve all user messages in this session first to clear their query caches
        user_msgs = session.query(ChatHistory).filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role == "user"
        ).all()
        for msg in user_msgs:
            query_hash = hashlib.md5(msg.content.encode('utf-8')).hexdigest()
            session.query(DBQueryCache).filter(
                DBQueryCache.query_hash == query_hash,
                DBQueryCache.user_id == msg.user_id
            ).delete()
            
        session.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
        session.query(ChatSession).filter(ChatSession.id == session_id).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error deleting chat session: {e}")
    finally:
        session.close()

def add_chat_message(user_id, session_id, role, content, intent=None, db_path="data/automotive.db"):
    """Saves a new chat message to the database under a session and returns its ID."""
    session = get_session(db_path)
    try:
        msg = ChatHistory(user_id=user_id, session_id=session_id, role=role, content=content, intent=intent)
        session.add(msg)
        session.commit()
        return msg.id
    except Exception as e:
        session.rollback()
        print(f"Error saving chat message: {e}")
        return None
    finally:
        session.close()

def get_user_chat_history(user_id, db_path="data/automotive.db", limit=50):
    """Fallback function for loading chat history globally or for the first session."""
    migrate_db_for_sessions(db_path)
    session = get_session(db_path)
    try:
        latest_session = session.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).first()
        if latest_session:
            session_id = latest_session.id
            session.close()
            return get_session_chat_history(user_id, session_id, db_path, limit)
        
        rows = session.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.timestamp.asc()).limit(limit).all()
        return [{"id": r.id, "role": r.role, "content": r.content, "intent": r.intent} for r in rows]
    finally:
        try:
            session.close()
        except Exception:
            pass
