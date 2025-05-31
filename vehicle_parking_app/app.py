from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime

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

# User Dashboard
@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect('/login')
    return render_template('user_dashboard.html', username=session.get('username'))

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

# View All Users and Spot Info
@app.route('/admin/users')
def view_users():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    users = conn.execute('''
        SELECT u.username, u.full_name, r.spot_id, r.parking_timestamp, r.leaving_timestamp
        FROM users u
        LEFT JOIN Reservation r ON u.id = r.user_id
        WHERE u.role = 'user'
    ''').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
