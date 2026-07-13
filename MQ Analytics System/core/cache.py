# =====================================================
# ✅ EMBEDDING & QUERY CACHING
# =====================================================
import hashlib
import json
import time
import datetime
import numpy as np
import pandas as pd
from core.paths import get_db_path
from core.database import get_session, QueryCache as DBQueryCache, EmbeddingCache as DBEmbeddingCache

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return {"__dataframe__": obj.to_dict(orient='records')}
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def custom_json_decoder(dct):
    if "__dataframe__" in dct:
        return pd.DataFrame(dct["__dataframe__"])
    return dct

class QueryCache:
    def __init__(self, db_path=None, max_ram_entries=200):
        if db_path is None:
            from core.config import DB_PATH
            db_path = DB_PATH
        self.db_path = get_db_path(db_path)
        self.ram_cache = {} # L1: query_hash -> result_dict
        self.max_ram_entries = max_ram_entries

    def _get_hash(self, key_str):
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, query_text, user_id=0):
        """Gets cached query result from RAM (L1) or DB (L2)."""
        query_hash = self._get_hash(query_text)
        
        # Check L1 (RAM)
        if query_hash in self.ram_cache:
            entry = self.ram_cache[query_hash]
            if entry["expires_at"] > time.time():
                return entry["data"]
            else:
                del self.ram_cache[query_hash]

        # Check L2 (SQLite via SQLAlchemy)
        session = get_session(self.db_path)
        try:
            row = session.query(DBQueryCache).filter(
                DBQueryCache.query_hash == query_hash,
                (DBQueryCache.user_id == user_id) | (DBQueryCache.user_id == 0)
            ).first()
            
            if row:
                expires_timestamp = row.expires_at.timestamp()
                if expires_timestamp > time.time():
                    data = json.loads(row.result_json, object_hook=custom_json_decoder)
                    # Cache in L1
                    self.ram_cache[query_hash] = {
                        "data": data,
                        "expires_at": expires_timestamp
                    }
                    self._prune_ram_cache()
                    return data
                else:
                    session.delete(row)
                    session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error reading query cache: {e}")
        finally:
            session.close()
        return None

    def set(self, query_text, user_id, data, ttl_seconds=30*86400):
        """Caches query results in RAM (L1) and DB (L2)."""
        query_hash = self._get_hash(query_text)
        expires_timestamp = time.time() + ttl_seconds
        expires_dt = datetime.datetime.fromtimestamp(expires_timestamp)
        result_json = json.dumps(data, cls=CustomJSONEncoder)

        # Cache in L1
        self.ram_cache[query_hash] = {
            "data": data,
            "expires_at": expires_timestamp
        }
        self._prune_ram_cache()

        # Cache in L2
        session = get_session(self.db_path)
        try:
            cache_entry = session.query(DBQueryCache).filter(
                DBQueryCache.query_hash == query_hash,
                DBQueryCache.user_id == user_id
            ).first()
            
            if cache_entry:
                cache_entry.result_json = result_json
                cache_entry.expires_at = expires_dt
            else:
                cache_entry = DBQueryCache(
                    query_hash=query_hash,
                    user_id=user_id,
                    result_json=result_json,
                    expires_at=expires_dt
                )
                session.add(cache_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving query cache: {e}")
        finally:
            session.close()

    def delete(self, query_hash, user_id):
        session = get_session(self.db_path)
        try:
            session.query(DBQueryCache).filter(
                DBQueryCache.query_hash == query_hash,
                DBQueryCache.user_id == user_id
            ).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error deleting cache: {e}")
        finally:
            session.close()

    def _prune_ram_cache(self):
        if len(self.ram_cache) > self.max_ram_entries:
            now = time.time()
            expired = [k for k, v in self.ram_cache.items() if v["expires_at"] <= now]
            for k in expired:
                del self.ram_cache[k]
            
            while len(self.ram_cache) > self.max_ram_entries:
                first_key = next(iter(self.ram_cache))
                del self.ram_cache[first_key]


class EmbeddingCache:
    def __init__(self, db_path=None):
        if db_path is None:
            from core.config import DB_PATH
            db_path = DB_PATH
        self.db_path = get_db_path(db_path)

    def _get_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get(self, text):
        """Retrieves cached embedding array from DB if exists."""
        text_hash = self._get_hash(text)
        session = get_session(self.db_path)
        try:
            row = session.query(DBEmbeddingCache).filter(DBEmbeddingCache.text_hash == text_hash).first()
            if row:
                blob = row.embedding_blob
                return np.frombuffer(blob, dtype=np.float32)
        except Exception as e:
            print(f"Error loading embedding cache: {e}")
        finally:
            session.close()
        return None

    def set(self, text, embedding):
        """Caches embedding array in DB."""
        text_hash = self._get_hash(text)
        blob = embedding.astype(np.float32).tobytes()
        
        session = get_session(self.db_path)
        try:
            cache_entry = session.query(DBEmbeddingCache).filter(DBEmbeddingCache.text_hash == text_hash).first()
            if cache_entry:
                cache_entry.embedding_blob = blob
            else:
                cache_entry = DBEmbeddingCache(
                    text_hash=text_hash,
                    embedding_blob=blob
                )
                session.add(cache_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving embedding cache: {e}")
        finally:
            session.close()
