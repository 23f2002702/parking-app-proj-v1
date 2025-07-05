from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import math
from dateutil import parser  

app = Flask(__name__)
app.secret_key = 'secret123'  # for session handling

def get_db_connection():
    conn = sqlite3.connect('database/parking.db')
    conn.row_factory = sqlite3.Row
    return conn

# === ROUTES ===

# Home → Redirect to login
@app.route('/')
def home():
    return redirect('/login')

# Register page (for users only)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (full_name, username, password, role) VALUES (?, ?, ?, ?)",
                         (fullname, username, password, 'user'))
            conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "⚠️ Username already exists!"
        finally:
            conn.close()
    return render_template('register.html')

# Login (for both Admin and Users)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                            (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            if user['role'] == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            return "❌ Invalid username or password"
    return render_template('login.html')

# Dashboard with Lots and Spot Status
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    lots = conn.execute('SELECT * FROM parking_lot').fetchall()

    spot_counts = {}
    for lot in lots:
        counts = conn.execute('''
            SELECT status, COUNT(*) as count FROM parking_spot
            WHERE lot_id = ?
            GROUP BY status
        ''', (lot['id'],)).fetchall()
        spot_counts[lot['id']] = {row['status']: row['count'] for row in counts}
    

    conn.close()
    return render_template('admin_dashboard.html', lots=lots, spot_counts=spot_counts)

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect('/login')

    user_id = session.get('user_id')
    conn = get_db_connection()

    # Get user's current active reservation (if any)
    reservation = conn.execute('''
        SELECT R.*, P.lot_id, L.name AS lot_name
        FROM Reservation R
        JOIN Parking_spot P ON R.spot_id = P.id
        JOIN Parking_lot L ON P.lot_id = L.id
        WHERE R.user_id = ? AND R.leaving_timestamp IS NULL
    ''', (user_id,)).fetchone()

    # All lots and spot availability
    lots = conn.execute('SELECT * FROM parking_lot').fetchall()
    spot_availability = {}
    for lot in lots:
        available = conn.execute('''
            SELECT COUNT(*) FROM parking_spot
            WHERE lot_id = ? AND status = 'A'
        ''', (lot['id'],)).fetchone()[0]
        spot_availability[lot['id']] = available

    # User's past reservation history 
    history = conn.execute('''
        SELECT R.*, P.lot_id, L.name AS lot_name
        FROM Reservation R
        JOIN Parking_spot P ON R.spot_id = P.id
        JOIN Parking_lot L ON P.lot_id = L.id
        WHERE R.user_id = ? AND R.leaving_timestamp IS NOT NULL
        ORDER BY R.parking_timestamp DESC
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('user_dashboard.html',
                           username=session.get('username'),
                           lots=lots,
                           spot_availability=spot_availability,
                           reservation=reservation,
                           history=history)

# Reserve first available spot 
@app.route('/user/reserve/<int:lot_id>')
def reserve_spot(lot_id):
    if session.get('role') != 'user':
        return redirect('/login')

    user_id = session.get('user_id')
    now = datetime.now()

    conn = get_db_connection()

    # Check if user already has active reservation
    existing = conn.execute('''
        SELECT * FROM Reservation
        WHERE user_id = ? AND leaving_timestamp IS NULL
    ''', (user_id,)).fetchone()

    if existing:
        conn.close()
        return "⚠️ You already have an active reservation."

    # Find first available spot **only in the chosen lot**
    spot = conn.execute('''
        SELECT * FROM Parking_spot
        WHERE status = 'A' AND lot_id = ?
        ORDER BY id ASC
        LIMIT 1
    ''', (lot_id,)).fetchone()

    if not spot:
        conn.close()
        return "🚫 No spots available in this parking lot at the moment."

    # Mark spot as occupied
    conn.execute('UPDATE Parking_spot SET status = "O" WHERE id = ?', (spot['id'],))

    # Create reservation with parking_timestamp set now
    conn.execute('''
        INSERT INTO Reservation (spot_id, user_id, parking_timestamp)
        VALUES (?, ?, ?)
    ''', (spot['id'], user_id, now.strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()
    return redirect('/user/dashboard')


# Log parking time
@app.route('/user/occupy')
def occupy_spot():
    if session.get('role') != 'user':
        return redirect('/login')

    user_id = session.get('user_id')
    now = datetime.now()

    conn = get_db_connection()
    conn.execute('''
        UPDATE Reservation
        SET parking_timestamp = ?
        WHERE user_id = ? AND leaving_timestamp IS NULL
    ''', (now, user_id))
    conn.commit()
    conn.close()
    return redirect('/user/dashboard')

# Release spot and calculate cost 
@app.route('/user/release')
def release_spot():
    if session.get('role') != 'user':
        return redirect('/login')

    user_id = session.get('user_id')
    now = datetime.now()

    conn = get_db_connection()

    # Get active reservation with price info
    reservation = conn.execute('''
        SELECT R.id, R.spot_id, R.parking_timestamp, L.price_per_hour
        FROM Reservation R
        JOIN Parking_spot P ON R.spot_id = P.id
        JOIN Parking_lot L ON P.lot_id = L.id
        WHERE R.user_id = ? AND R.leaving_timestamp IS NULL
    ''', (user_id,)).fetchone()

    if not reservation:
        conn.close()
        return "⚠️ No active reservation found."

    # Parse start time from DB string
    start = parser.parse(reservation['parking_timestamp'])
    duration_minutes = (now - start).total_seconds() / 60  # total minutes parked

    # Round up to nearest full hour
    hours = math.ceil(duration_minutes / 60)
    cost = hours * reservation['price_per_hour']

    # Update reservation with leaving time and cost
    conn.execute('''
        UPDATE Reservation
        SET leaving_timestamp = ?, parking_cost = ?
        WHERE id = ?
    ''', (now.strftime('%Y-%m-%d %H:%M:%S'), cost, reservation['id']))

    # Free the spot
    conn.execute('UPDATE Parking_spot SET status = "A" WHERE id = ?', (reservation['spot_id'],))

    conn.commit()
    conn.close()
    return redirect('/user/dashboard')


# Create Parking Lot (with Auto-creating Spots) 
@app.route('/admin/create_lot', methods=['GET', 'POST'])
def create_lot():
    if session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = float(request.form['price_per_hour'])
        max_spots = int(request.form['max_spots'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO parking_lot (name, address, pin_code, price_per_hour, max_spots)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, address, pin_code, price, max_spots))
        lot_id = cursor.lastrowid

        for _ in range(max_spots):
            cursor.execute('INSERT INTO parking_spot (lot_id, status) VALUES (?, ?)', (lot_id, 'A'))
        
        conn.commit()
        conn.close()
        return redirect('/admin/dashboard')

    return render_template('admin_create_lot.html')

# Edit Parking Lot
@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = float(request.form['price_per_hour'])
        conn.execute('''
            UPDATE parking_lot
            SET name=?, address=?, pin_code=?, price_per_hour=?
            WHERE id=?
        ''', (name, address, pin_code, price, lot_id))
        conn.commit()
        conn.close()
        return redirect('/admin/dashboard')

    lot = conn.execute('SELECT * FROM parking_lot WHERE id=?', (lot_id,)).fetchone()
    conn.close()
    return render_template('admin_edit_lot.html', lot=lot)

# Delete Lot (only if all spots are available)
@app.route('/admin/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    occupied = conn.execute('''
        SELECT COUNT(*) FROM parking_spot
        WHERE lot_id = ? AND status = 'O'
    ''', (lot_id,)).fetchone()[0]

    if occupied > 0:
        conn.close()
        return "Cannot delete this lot. Some spots are still occupied."

    conn.execute('DELETE FROM parking_spot WHERE lot_id = ?', (lot_id,))
    conn.execute('DELETE FROM parking_lot WHERE id = ?', (lot_id,))
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
