# =====================================================
# ✅ INBOX FOLDER WATCHER & AUTOMATIC ETL SERVICE
# =====================================================
import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.paths import get_inbox_path, get_db_path
from core.etl.pipeline import ingest_excel
from core.singletons import get_ingestion_tracker
from core.logger import get_logger

logger = get_logger(__name__)

class InboxHandler(FileSystemEventHandler):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.tracker = get_ingestion_tracker()
        self._processed_files = set()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = os.path.abspath(event.src_path)
        filename = os.path.basename(file_path)

        # Only process .xlsx and .csv files
        if not (filename.endswith('.xlsx') or filename.endswith('.csv')):
            return

        # Avoid processing temporary office lock/owner files
        if filename.startswith('~$'):
            return

        if file_path in self._processed_files:
            return

        logger.info(f"New file detected in inbox: {filename}")
        self._processed_files.add(file_path)

        # Wait a short moment to ensure the file copy is finished/fully written
        time.sleep(1.0)

        try:
            new_records = ingest_excel(file_path, self.db_path)
            count = len(new_records)
            logger.info(f"Automatically ingested {count} records from inbox file: {filename}")
            
            # Register in singletons tracker
            self.tracker.register_ingestion(filename, count)
        except Exception as e:
            logger.exception(f"Failed to automatically ingest {filename}")

def start_inbox_watcher(db_path=None):
    """Starts the background directory observer on data/inbox."""
    if db_path is None:
        db_path = get_db_path()

    inbox_dir = get_inbox_path()
    os.makedirs(inbox_dir, exist_ok=True)

    logger.info(f"Starting Inbox Watcher Service monitoring: {inbox_dir}")

    event_handler = InboxHandler(db_path)
    observer = Observer()
    observer.schedule(event_handler, path=inbox_dir, recursive=False)
    
    # Start the observer in a separate daemon thread
    watcher_thread = threading.Thread(target=observer.start, daemon=True)
    watcher_thread.start()
    
    # Return observer handle in case we want to stop it
    return observer
