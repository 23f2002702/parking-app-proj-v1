from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

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
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, password, 'user'))
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

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin_dashboard.html', username=session.get('username'))

# User Dashboard
@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect('/login')
    return render_template('user_dashboard.html', username=session.get('username'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
