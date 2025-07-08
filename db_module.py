import sqlite3
import threading
import time
import logging

class Database:
    def __init__(self, db_path='gps_data.db'):
        self.logger = logging.getLogger('GSS.Database')
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.lock = threading.Lock()
            self.create_tables()
            self.cache = []
            self.cache_limit = 100  # Number of records before flushing to DB
            self.flush_interval = 5  # seconds
            self.last_flush_time = time.time()
            self._start_flush_thread()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def create_tables(self):
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gps_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        latitude REAL,
                        longitude REAL,
                        hectares_covered REAL
                    )
                ''')
                self.conn.commit()
            self.logger.info("Database tables created or verified successfully")
        except Exception as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise

    def add_record(self, latitude, longitude, hectares_covered):
        try:
            with self.lock:
                self.cache.append((latitude, longitude, hectares_covered))
                current_time = time.time()
                if len(self.cache) >= self.cache_limit or (current_time - self.last_flush_time) >= self.flush_interval:
                    self.flush_cache()
        except Exception as e:
            self.logger.error(f"Error adding record to cache: {e}")

    def flush_cache(self):
        if not self.cache:
            return
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.executemany('''
                    INSERT INTO gps_data (latitude, longitude, hectares_covered)
                    VALUES (?, ?, ?)
                ''', self.cache)
                self.conn.commit()
                self.cache.clear()
                self.last_flush_time = time.time()
            self.logger.info("Database cache flushed successfully")
        except Exception as e:
            self.logger.error(f"Error flushing cache to database: {e}")

    def _start_flush_thread(self):
        def flush_periodically():
            while True:
                time.sleep(self.flush_interval)
                self.flush_cache()
        thread = threading.Thread(target=flush_periodically, daemon=True)
        thread.start()

    def close(self):
        try:
            self.flush_cache()
            self.conn.close()
            self.logger.info("Database connection closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}")
