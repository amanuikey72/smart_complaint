"""
database.py - Database setup, SQLite helpers, and realistic seed data for SmartComplaint AI.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from nlp_engine import analyze_complaint

def get_db_path():
    """Returns a writable path for SQLite database, supporting serverless / read-only environments."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_db = os.path.join(base_dir, "smart_complaint.db")
    
    # Check if running on serverless platform (e.g. Vercel) or read-only directory
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    is_readonly = not os.access(base_dir, os.W_OK)
    
    if is_serverless or is_readonly:
        import tempfile
        import shutil
        tmp_db = os.path.join(tempfile.gettempdir(), "smart_complaint.db")
        if not os.path.exists(tmp_db) and os.path.exists(default_db):
            try:
                shutil.copy2(default_db, tmp_db)
            except Exception as e:
                print(f"[Database] Could not copy DB to tmp: {e}")
        return tmp_db
    
    return default_path if 'default_path' in locals() else default_db

DB_PATH = get_db_path()

def get_db_connection():
    """Establishes SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables if they do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'citizen',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Complaints Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            priority TEXT NOT NULL,
            ai_score INTEGER NOT NULL,
            urgency TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            recommended_handling TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Activity Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            actor_name TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    
    # Run seed data if database was just created / empty
    seed_db_if_empty()

def seed_db_if_empty():
    """Populates database with realistic default admin, citizens, and complaints if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()['count']

    if user_count == 0:
        print("[Database] Seeding initial users and complaints...")
        
        # 1. Create Default Users
        admin_pass = generate_password_hash("admin123")
        citizen_pass = generate_password_hash("user123")

        users_to_seed = [
            ("Chief Administrator", "admin@smartcomplaint.gov.in", admin_pass, "admin", "+91 98765 43210"),
            ("Rahul Sharma", "citizen@gmail.com", citizen_pass, "citizen", "+91 98123 45678"),
            ("Ananya Verma", "ananya@gmail.com", citizen_pass, "citizen", "+91 97234 56789"),
            ("Vikram Singh", "vikram@gmail.com", citizen_pass, "citizen", "+91 96345 67890"),
            ("Priya Patel", "priya@gmail.com", citizen_pass, "citizen", "+91 95456 78901")
        ]

        cursor.executemany('''
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', users_to_seed)
        conn.commit()

        # Fetch inserted user IDs
        cursor.execute("SELECT id, email FROM users")
        user_map = {row['email']: row['id'] for row in cursor.fetchall()}

        # 2. Create Realistic Seed Complaints
        raw_complaints = [
            {
                "user_email": "citizen@gmail.com",
                "title": "Severe Gas Leak and Sparking Wires in Market",
                "description": "Gas pipe leaking heavily near main junction market. Live electric transformer sparking overhead near residential apartments. High risk of explosion and fire, please dispatch team immediately!",
                "location": "Sector 14 Main Commercial Junction",
                "status": "In Progress",
                "tracking_id": "SC-2026-9101",
                "created_at": "2026-09-12 08:30:00",
                "admin_notes": "Emergency Response Team dispatched at 08:45 AM. Power grid shut off for safety."
            },
            {
                "user_email": "ananya@gmail.com",
                "title": "Major Water Pipe Burst Flooding 5th Avenue",
                "description": "Main water pipeline burst near metro station. Clean drinking water wasting rapidly and flooding lower floor shops. Traffic signal malfunctioning due to water logging.",
                "location": "5th Avenue Metro Gate 3",
                "status": "Pending",
                "tracking_id": "SC-2026-9102",
                "created_at": "2026-09-13 14:15:00",
                "admin_notes": None
            },
            {
                "user_email": "vikram@gmail.com",
                "title": "Uncovered Deep Open Manhole on Highway",
                "description": "Deep open sewer manhole without warning sign on fast lane highway. Two motorbikes barely avoided falling in. Extreme hazard at night time.",
                "location": "NH-48 Outer Ring Road Kilometre 12",
                "status": "In Progress",
                "tracking_id": "SC-2026-9103",
                "created_at": "2026-09-11 20:00:00",
                "admin_notes": "Barricade placed immediately by highway patrol. Permanent slab installation scheduled."
            },
            {
                "user_email": "priya@gmail.com",
                "title": "Sewage Overflow and Foul Smell near School",
                "description": "Sewer line backed up for past 3 days. Foul sewage water leaking on walking path taken by primary school children. Health hazard and mosquito breeding ground.",
                "location": "Greenwood Public School Road",
                "status": "Pending",
                "tracking_id": "SC-2026-9104",
                "created_at": "2026-09-13 09:10:00",
                "admin_notes": None
            },
            {
                "user_email": "citizen@gmail.com",
                "title": "Garbage Dump Accumulation in Park Corner",
                "description": "Municipal waste bins not emptied for 5 days. Overflowing trash causing foul odor and blocking park walking track.",
                "location": "Central Community Park Sector 8",
                "status": "Resolved",
                "tracking_id": "SC-2026-9105",
                "created_at": "2026-09-08 11:00:00",
                "admin_notes": "Sanitation truck cleared waste on Sept 9th and disinfected area."
            },
            {
                "user_email": "ananya@gmail.com",
                "title": "Streetlight Broken on 4th Cross Road",
                "description": "Three consecutive streetlights out of order. Dark alley creating security concerns for late evening commuters.",
                "location": "4th Cross Road Behind City Library",
                "status": "Resolved",
                "tracking_id": "SC-2026-9106",
                "created_at": "2026-09-05 19:45:00",
                "admin_notes": "LED bulbs replaced by Electrical Works Dept."
            },
            {
                "user_email": "vikram@gmail.com",
                "title": "Potholes Causing Traffic Delay near Bridge",
                "description": "Deep asphalt crater on left lane slowing down morning traffic. Requires road patching.",
                "location": "River Flyover South Ramp",
                "status": "Pending",
                "tracking_id": "SC-2026-9107",
                "created_at": "2026-09-10 16:20:00",
                "admin_notes": None
            },
            {
                "user_email": "priya@gmail.com",
                "title": "Request for Additional Trash Bin near Food Court",
                "description": "Suggestion to install extra recycling and wet waste bins near the evening street food zone.",
                "location": "Civic Center Food Court Zone",
                "status": "In Progress",
                "tracking_id": "SC-2026-9108",
                "created_at": "2026-09-04 10:00:00",
                "admin_notes": "Requisition sent to Urban Waste Management."
            },
            {
                "user_email": "citizen@gmail.com",
                "title": "Hazardous Tree Branch Leaning over Electric Line",
                "description": "Large dead tree branch snapped during storm, hanging precariously over high tension electrical line. Could break wires any minute.",
                "location": "Oakwood Enclave Block B",
                "status": "Resolved",
                "tracking_id": "SC-2026-9109",
                "created_at": "2026-08-28 15:30:00",
                "admin_notes": "Horticulture team trimmed branch safely."
            },
            {
                "user_email": "ananya@gmail.com",
                "title": "Loud Commercial Speaker Noise at Midnight",
                "description": "Commercial warehouse operating heavy industrial speakers past 11 PM violating residential noise control regulations.",
                "location": "Industrial Extension Phase 2",
                "status": "Rejected",
                "tracking_id": "SC-2026-9110",
                "created_at": "2026-08-20 23:50:00",
                "admin_notes": "Referred to Local Police Licensing Department as out of municipal purview."
            }
        ]

        for c_data in raw_complaints:
            user_id = user_map[c_data["user_email"]]
            analysis = analyze_complaint(c_data["title"], c_data["description"])

            cursor.execute('''
                INSERT INTO complaints (
                    tracking_id, user_id, title, description, category, location,
                    priority, ai_score, urgency, risk_level, recommended_handling,
                    status, admin_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                c_data["tracking_id"],
                user_id,
                c_data["title"],
                c_data["description"],
                analysis["category"],
                c_data["location"],
                analysis["priority"],
                analysis["score"],
                analysis["urgency"],
                analysis["risk_level"],
                analysis["recommended_handling"],
                c_data["status"],
                c_data["admin_notes"],
                c_data["created_at"],
                c_data["created_at"]
            ))
            
            complaint_id = cursor.lastrowid
            
            # Log initial activity
            cursor.execute('''
                INSERT INTO activity_logs (complaint_id, action, actor_name, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (complaint_id, "Complaint Submitted & AI Analyzed", "SmartComplaint AI Engine", c_data["created_at"]))

            if c_data["status"] != "Pending":
                cursor.execute('''
                    INSERT INTO activity_logs (complaint_id, action, actor_name, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (complaint_id, f"Status updated to {c_data['status']}", "Chief Administrator", c_data["created_at"]))

        conn.commit()
        print("[Database] Seeded 5 users and 10 realistic AI-scored complaints successfully.")

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
