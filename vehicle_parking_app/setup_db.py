import sqlite3

# Create or connect to the SQLite database (in the current folder)
conn = sqlite3.connect('parking.db')
cursor = conn.cursor()

# USERS table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'user')) NOT NULL
);
''')

# PARKING LOTS table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Parking_lot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_per_hour REAL NOT NULL,
    address TEXT,
    pin_code TEXT,
    max_spots INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# PARKING SPOTS table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Parking_spot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    spot_number TEXT,
    status TEXT CHECK(status IN ('A', 'O')) DEFAULT 'A',
    FOREIGN KEY (lot_id) REFERENCES Parking_lot(id)
);
''')

# RESERVATIONS table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    parking_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leaving_timestamp TIMESTAMP,
    parking_cost REAL,
    FOREIGN KEY (spot_id) REFERENCES Parking_spot(id),
    FOREIGN KEY (user_id) REFERENCES Users(id)
);
''')

# Insert default admin user
cursor.execute("SELECT * FROM Users WHERE username = 'Admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users (full_name,username, password, role) VALUES (?, ?, ?, ?)", 
                   ('Admin','admin', 'admin123', 'admin'))
    print("✅ Admin account created.")

conn.commit()
conn.close()
print("✅ Database setup completed.")


