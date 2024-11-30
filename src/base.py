from src.config import DATABASE

class Base:
    database:str = DATABASE

    def __init__(self, database:str = DATABASE) -> None:
        self.database = database

    def get_db_connection(database):
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_table_exists():
        """Ensure that the products table exists in the database."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        ''')
        conn.commit()
        conn.close()

    # Voice recording function
    def record_voice(duration=5, filename:str ="voice_input.wav") -> str:
        """Record audio for a given duration and save to a file."""
        fs = 44100  # Sample rate
        print("Recording...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        # sd.wait()  # Wait until recording is finished
        time.sleep(duration)
        write(filename, fs, recording)  # Save as WAV file
        print("Recording complete.")
        return filename
