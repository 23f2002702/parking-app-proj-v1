# Vehicle Parking App (V1)

A web-based Vehicle Parking Management System designed for managing parking slots in multiple lots, allowing users to reserve and release parking spaces, and enabling admins to monitor and control the overall system.

---

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, Bootstrap (minimal use)
- **Database:** SQLite
- **Templating Engine:** Jinja2

---

## Features

### User Side

- Register/Login  
- Book the first available parking spot  
- Mark as "occupied" when parked  
- Release spot to calculate cost  
- View personal reservation history (with time and cost)

###  Admin Side

- Login as admin  
- Create, edit, delete parking lots  
- View available/occupied spot counts  
- View all registered users  
- View full parking summary (history of all reservations)

---

## Project Milestones

### Milestone 1: Database Models & Schema
- Designed and created `Users`, `Parking_lot`, `Parking_spot`, and `Reservation` tables using SQLite.
- Setup script to initialize the database (`setup_db.py`).

### Milestone 2: User & Admin Authentication
- Built registration and login system for users.
- Added admin login via pre-created account.
- Session-based authentication using Flask.

### Milestone 3: Parking Lot & Spot Management
- Admin can create new parking lots with configurable price and max spots.
- Spot status auto-handled (`Available` / `Occupied`).
- Admin dashboard shows spot availability per lot.

### Milestone 4: Booking and Releasing Parking Spots
- Users can book the first available spot in any lot.
- "Occupy" action sets `parking_timestamp`.
- "Release" action sets `leaving_timestamp` and updates spot status.

### Milestone 5: Reservation History and Summary
- Users can view their own booking history (including lot name, time, cost).
- Admin can view **all users’** complete parking summaries.

### Milestone 6: Slot Time Calculation and Cost
- Total parking duration is calculated using timestamps.
- Cost = `ceil(duration in hours) × price_per_hour` is computed and stored.
- Cost shown in both user and admin views.

---

## Project Structure

```
├── app.py                  # Main Flask app
├── setup_db.py             # Initializes DB schema
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── user_dashboard.html
│   ├── admin_dashboard.html
│   ├── admin_create_lot.html
│   ├── admin_edit_lot.html
│   ├── admin_users.html
│   └── admin_parking_summary.html
├── static/
│   └── styles.css
├── database/
│   └── parking.db
```

---


