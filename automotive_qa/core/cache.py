import sqlite3
import hashlib
import json
import time
import datetime
import numpy as np
import pandas as pd
from core.paths import get_db_path

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
    def __init__(self, db_path="data/automotive.db", max_ram_entries=200):
        self.db_path = get_db_path(db_path)
        self.ram_cache = {} # L1: query_hash -> result_dict
        self.max_ram_entries = max_ram_entries

    def _get_hash(self, key_str):
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, query_text, user_id=0):
        """
        Gets a cached query result for a given query text and user ID.
        Checks L1 (RAM) first, then L2 (SQLite).
        """
        query_hash = self._get_hash(query_text)
        
        # Check L1 (RAM)
        if query_hash in self.ram_cache:
            entry = self.ram_cache[query_hash]
            if entry["expires_at"] > time.time():
                return entry["data"]
            else:
                del self.ram_cache[query_hash]

        # Check L2 (SQLite)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT result_json, expires_at 
            FROM query_cache 
            WHERE query_hash = ? AND (user_id = ? OR user_id = 0);
        """, (query_hash, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result_json, expires_at_str = row
            try:
                expires_at = datetime.datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
                expires_timestamp = expires_at.timestamp()
            except ValueError:
                expires_timestamp = 0.0
                
            if expires_timestamp > time.time():
                data = json.loads(result_json, object_hook=custom_json_decoder)
                # Store in L1
                self.ram_cache[query_hash] = {
                    "data": data,
                    "expires_at": expires_timestamp
                }
                self._prune_ram_cache()
                return data
            else:
                # Expired: delete from DB
                self.delete(query_hash, user_id)
                
        return None

    def set(self, query_text, user_id, data, ttl_seconds=7200):
        """
        Caches a query result for a given query text.
        Writes to both L1 (RAM) and L2 (SQLite).
        """
        query_hash = self._get_hash(query_text)
        expires_timestamp = time.time() + ttl_seconds
        expires_str = datetime.datetime.fromtimestamp(expires_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        result_json = json.dumps(data, cls=CustomJSONEncoder)

        # Write to L1 (RAM)
        self.ram_cache[query_hash] = {
            "data": data,
            "expires_at": expires_timestamp
        }
        self._prune_ram_cache()

        # Write to L2 (SQLite)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO query_cache (query_hash, user_id, result_json, expires_at)
                VALUES (?, ?, ?, ?);
            """, (query_hash, user_id, result_json, expires_str))
            conn.commit()
        except Exception as e:
            print(f"Error saving to query cache: {e}")
        finally:
            conn.close()

    def delete(self, query_hash, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM query_cache WHERE query_hash = ? AND user_id = ?;", (query_hash, user_id))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def _prune_ram_cache(self):
        if len(self.ram_cache) > self.max_ram_entries:
            # Simple FIFO or expiration pruning
            # Prune expired entries first
            now = time.time()
            expired = [k for k, v in self.ram_cache.items() if v["expires_at"] <= now]
            for k in expired:
                del self.ram_cache[k]
            
            # If still too large, delete first key
            while len(self.ram_cache) > self.max_ram_entries:
                first_key = next(iter(self.ram_cache))
                del self.ram_cache[first_key]


class EmbeddingCache:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)

    def _get_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get(self, text):
        """Retrieves cached embedding array from DB if exists."""
        text_hash = self._get_hash(text)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT embedding_blob FROM embedding_cache WHERE text_hash = ?;", (text_hash,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Load numpy array from blob
            blob = row[0]
            embedding = np.frombuffer(blob, dtype=np.float32)
            return embedding
        return None

    def set(self, text, embedding):
        """Caches embedding array in DB."""
        text_hash = self._get_hash(text)
        blob = embedding.astype(np.float32).tobytes()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO embedding_cache (text_hash, embedding_blob)
                VALUES (?, ?);
            """, (text_hash, sqlite3.Binary(blob)))
            conn.commit()
        except Exception as e:
            print(f"Error saving embedding to cache: {e}")
        finally:
            conn.close()
