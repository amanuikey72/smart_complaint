"""
app.py - Main Flask Application for SmartComplaint AI Governance Platform.
"""

import os
import re
import random
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, init_db
from nlp_engine import analyze_complaint

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartcomplaint-ai-super-secret-key-2026")

# Ensure DB initialized on startup
init_db()


# -------------------------------------------------------------------
# Authentication Decorators & Middleware
# -------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in as Administrator.", "warning")
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_user():
    """Make current session user available in Jinja2 templates."""
    return dict(
        current_user={
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': session.get('user_email'),
            'role': session.get('role', 'guest')
        } if 'user_id' in session else None
    )


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    Live AI Complaint Analysis Endpoint.
    Accepts JSON: { "title": "...", "description": "...", "category": "..." }
    Returns real NLP priority score, urgency, signals, and explanation.
    """
    data = request.get_json() or {}
    title = data.get('title', '')
    description = data.get('description', '')
    category = data.get('category', None)

    if not title.strip() and not description.strip():
        return jsonify({
            "error": "No text provided for AI analysis",
            "score": 0,
            "priority": "LOW",
            "priority_badge": "🟢 LOW",
            "category": "Pending Input",
            "urgency": "None",
            "risk_level": "Minimal",
            "recommended_handling": "Awaiting complaint details...",
            "detected_signals": [],
            "explanation_factors": ["Please enter title and description to trigger AI analysis."]
        }), 400

    analysis_result = analyze_complaint(title, description, category)
    return jsonify(analysis_result)


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """
    Real Database Statistics API for Chart.js & Metrics.
    Returns real metrics from SQLite database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total & Status Counts
    cursor.execute("SELECT COUNT(*) as total FROM complaints")
    total_complaints = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Pending'")
    pending_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Resolved'")
    resolved_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Rejected'")
    rejected_count = cursor.fetchone()['cnt']

    # Priority Counts
    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'CRITICAL'")
    critical_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'HIGH'")
    high_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'MEDIUM'")
    medium_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'LOW'")
    low_count = cursor.fetchone()['cnt']

    # Category Counts
    cursor.execute("SELECT category, COUNT(*) as cnt FROM complaints GROUP BY category")
    category_rows = cursor.fetchall()
    category_counts = {row['category']: row['cnt'] for row in category_rows}

    # Ensure all key categories exist in map
    all_categories = [
        "Safety & Security", "Health & Sanitation", "Water & Utilities",
        "Infrastructure & Roads", "Environment & Public Spaces"
    ]
    for cat in all_categories:
        if cat not in category_counts:
            category_counts[cat] = 0

    # User Count
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'citizen'")
    total_citizens = cursor.fetchone()['cnt']

    # Monthly Trend (Past 6 Months)
    # Using strftime or datetime grouping
    monthly_labels = []
    monthly_data = []
    
    # Generate past 6 month labels
    now = datetime.now()
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=i*30)
        month_str = month_date.strftime("%b %Y")
        month_db_fmt = month_date.strftime("%Y-%m")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE strftime('%Y-%m', created_at) = ?", (month_db_fmt,))
        cnt = cursor.fetchone()['cnt']
        
        monthly_labels.append(month_str)
        monthly_data.append(cnt)

    conn.close()

    return jsonify({
        "total_complaints": total_complaints,
        "pending": pending_count,
        "in_progress": in_progress_count,
        "resolved": resolved_count,
        "rejected": rejected_count,
        "critical": critical_count,
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "total_citizens": total_citizens,
        "categories": category_counts,
        "monthly_trend": {
            "labels": monthly_labels,
            "data": monthly_data
        }
    })


# -------------------------------------------------------------------
# Public Routes
# -------------------------------------------------------------------

@app.route('/')
def index():
    """Public Landing Page."""
    return render_template('index.html')


@app.route('/track', methods=['GET', 'POST'])
@app.route('/track/<tracking_id>', methods=['GET'])
def track_complaint(tracking_id=None):
    """Public / Accessible Complaint Tracking Portal."""
    complaint = None
    timeline = []
    search_query = tracking_id or request.args.get('search_id') or (request.form.get('tracking_id') if request.method == 'POST' else None)

    if search_query:
        search_query = search_query.strip().upper()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Support searching by tracking_id (SC-2026-XXXX) or numeric DB ID
        if search_query.isdigit():
            cursor.execute("SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE c.id = ?", (int(search_query),))
        else:
            cursor.execute("SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE UPPER(c.tracking_id) = ?", (search_query,))
        
        complaint = cursor.fetchone()

        if complaint:
            cursor.execute("SELECT * FROM activity_logs WHERE complaint_id = ? ORDER BY timestamp ASC", (complaint['id'],))
            timeline = cursor.fetchall()
        else:
            flash(f"No complaint found matching ID '{search_query}'. Please verify tracking code.", "danger")

        conn.close()

    return render_template('track.html', complaint=complaint, timeline=timeline, search_query=search_query)


# -------------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Citizen Registration Page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        
        form_data = {
            'name': name,
            'email': email,
            'phone': phone
        }

        if not name or not email or not password:
            flash("All required fields must be filled out.", "danger")
            return render_template('register.html', form_data=form_data)

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template('register.html', form_data=form_data)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', form_data=form_data)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', form_data=form_data)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if cursor.fetchone():
                conn.close()
                flash("An account with this email already exists. Please login.", "warning")
                return redirect(url_for('login'))

            password_hash = generate_password_hash(password)
            cursor.execute("INSERT INTO users (name, email, password_hash, role, phone) VALUES (?, ?, ?, 'citizen', ?)",
                           (name, email, password_hash, phone))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()

            # Log user in directly
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            session['role'] = 'citizen'

            flash("Account created successfully! Welcome to SmartComplaint AI.", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"An unexpected database error occurred during registration. Please try again.", "danger")
            return render_template('register.html', form_data=form_data)

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Dual / Unified Login Page (Citizen and Admin)."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_overview'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = user['role']

            flash(f"Welcome back, {user['name']}!", "success")
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_overview'))
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email address or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout handler."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('index'))


# -------------------------------------------------------------------
# Citizen Portal Routes
# -------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    """Citizen Dashboard."""
    if session.get('role') == 'admin':
        return redirect(url_for('admin_overview'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # User's complaint stats
    cursor.execute("SELECT COUNT(*) as total FROM complaints WHERE user_id = ?", (user_id,))
    total_complaints = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status = 'Pending'", (user_id,))
    pending_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status = 'In Progress'", (user_id,))
    in_progress_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status = 'Resolved'", (user_id,))
    resolved_count = cursor.fetchone()['cnt']

    # Fetch 5 most recent complaints
    cursor.execute("SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
    recent_complaints = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_complaints=total_complaints,
                           pending_count=pending_count,
                           in_progress_count=in_progress_count,
                           resolved_count=resolved_count,
                           recent_complaints=recent_complaints)


@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    """Submit New Complaint Page with Live AI Analysis."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Infrastructure & Roads')
        location = request.form.get('location', '').strip()

        if not title or not description or not location:
            flash("Please complete all required fields.", "danger")
            return render_template('complaint_new.html')

        # Run AI analysis on backend
        ai_data = analyze_complaint(title, description, category)

        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        # Guarantee unique tracking ID generation
        while True:
            random_suffix = random.randint(1000, 9999)
            tracking_id = f"SC-{datetime.now().year}-{random_suffix}"
            cursor.execute("SELECT id FROM complaints WHERE tracking_id = ?", (tracking_id,))
            if not cursor.fetchone():
                break

        try:
            cursor.execute('''
                INSERT INTO complaints (
                    tracking_id, user_id, title, description, category, location,
                    priority, ai_score, urgency, risk_level, recommended_handling, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
            ''', (
                tracking_id,
                user_id,
                title,
                description,
                ai_data['category'],
                location,
                ai_data['priority'],
                ai_data['score'],
                ai_data['urgency'],
                ai_data['risk_level'],
                ai_data['recommended_handling']
            ))
            
            complaint_id = cursor.lastrowid

            # Log activity
            cursor.execute('''
                INSERT INTO activity_logs (complaint_id, action, actor_name)
                VALUES (?, ?, ?)
            ''', (complaint_id, "Complaint Submitted & AI Prioritized", session.get('user_name', 'Citizen')))

            conn.commit()
            conn.close()

            flash(f"Complaint #{tracking_id} submitted successfully!", "success")
            return redirect(url_for('complaint_result', id=complaint_id))
        except Exception as e:
            conn.close()
            app.logger.error(f"Error submitting complaint: {e}", exc_info=True)
            flash("A database error occurred while filing your complaint. Please try again.", "danger")
            return render_template('complaint_new.html')

    return render_template('complaint_new.html')


@app.route('/complaint/result/<int:id>')
@login_required
def complaint_result(id):
    """Post-submission confirmation page."""
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM complaints WHERE id = ?", (id,))
    complaint = cursor.fetchone()
    conn.close()

    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('complaint_result.html', complaint=complaint)


@app.route('/complaints')
@app.route('/my-complaints')
@login_required
def my_complaints():
    """Citizen My Complaints page with search and multi-filtering."""
    user_id = session['user_id']
    is_admin = (session.get('role') == 'admin')

    priority_filter = request.args.get('priority')
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    search_term = request.args.get('search')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE 1=1"
    params = []

    if not is_admin:
        query += " AND c.user_id = ?"
        params.append(user_id)

    if priority_filter and priority_filter != 'ALL':
        query += " AND c.priority = ?"
        params.append(priority_filter)

    if status_filter and status_filter != 'ALL':
        query += " AND c.status = ?"
        params.append(status_filter)

    if category_filter and category_filter != 'ALL':
        query += " AND c.category = ?"
        params.append(category_filter)

    if search_term:
        query += " AND (c.title LIKE ? OR c.description LIKE ? OR c.tracking_id LIKE ? OR c.location LIKE ?)"
        term = f"%{search_term.strip()}%"
        params.extend([term, term, term, term])

    query += " ORDER BY c.created_at DESC"
    cursor.execute(query, params)
    complaints = cursor.fetchall()
    conn.close()

    return render_template('complaints.html', complaints=complaints,
                           priority_filter=priority_filter,
                           status_filter=status_filter,
                           category_filter=category_filter,
                           search_term=search_term)


@app.route('/complaint/<int:id>')
@login_required
def complaint_detail(id):
    """Detailed Complaint View & Resolution Timeline."""
    user_id = session['user_id']
    role = session.get('role')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name, COALESCE(u.email, 'N/A') as citizen_email, COALESCE(u.phone, 'N/A') as citizen_phone FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE c.id = ?", (id,))
    complaint = cursor.fetchone()

    if not complaint:
        conn.close()
        flash("Complaint not found.", "danger")
        return redirect(url_for('dashboard'))

    # Security check: citizens can only view their own complaint
    if role != 'admin' and complaint['user_id'] != user_id:
        conn.close()
        flash("Unauthorized access.", "danger")
        return redirect(url_for('dashboard'))

    # Re-run explainable analysis for rendering breakdown factors
    ai_breakdown = analyze_complaint(complaint['title'], complaint['description'], complaint['category'])

    # Fetch activity timeline
    cursor.execute("SELECT * FROM activity_logs WHERE complaint_id = ? ORDER BY timestamp ASC", (id,))
    timeline = cursor.fetchall()
    conn.close()

    return render_template('complaint_detail.html', complaint=complaint, ai_breakdown=ai_breakdown, timeline=timeline)


# -------------------------------------------------------------------
# Admin Command Center Routes
# -------------------------------------------------------------------

@app.route('/admin')
@app.route('/admin/overview')
@admin_required
def admin_overview():
    """Admin Command Center Overview Dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # KPI counts
    cursor.execute("SELECT COUNT(*) as cnt FROM complaints")
    total_complaints = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'CRITICAL'")
    critical_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE priority = 'HIGH'")
    high_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Pending'")
    pending_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Resolved'")
    resolved_count = cursor.fetchone()['cnt']

    # Fetch top 5 critical/high priority active complaints
    cursor.execute('''
        SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.status != 'Resolved' AND c.status != 'Rejected'
        ORDER BY c.ai_score DESC, c.created_at DESC
        LIMIT 5
    ''')
    priority_alerts = cursor.fetchall()

    conn.close()

    return render_template('admin/overview.html',
                           total_complaints=total_complaints,
                           critical_count=critical_count,
                           high_count=high_count,
                           pending_count=pending_count,
                           in_progress_count=in_progress_count,
                           resolved_count=resolved_count,
                           priority_alerts=priority_alerts)


@app.route('/admin/priority-monitor')
@admin_required
def admin_priority_monitor():
    """Dedicated AI Priority Monitor ranking complaints by AI urgency score."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.*, COALESCE(u.name, 'Citizen') as citizen_name, COALESCE(u.email, 'N/A') as citizen_email
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.id
        ORDER BY c.ai_score DESC, c.created_at DESC
    ''')
    complaints = cursor.fetchall()
    conn.close()

    return render_template('admin/priority_monitor.html', complaints=complaints)


@app.route('/admin/complaints')
@admin_required
def admin_complaints():
    """Admin Complaint Matrix."""
    return my_complaints()


@app.route('/admin/complaint/<int:id>')
@admin_required
def admin_complaint_detail(id):
    """Admin detailed complaint view."""
    return complaint_detail(id)


@app.route('/admin/update-status/<int:id>', methods=['POST'])
@admin_required
def admin_update_status(id):
    """Update Complaint Status and Add Admin Notes."""
    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '').strip()

    valid_statuses = ['Pending', 'In Progress', 'Resolved', 'Rejected']
    if new_status not in valid_statuses:
        flash("Invalid status value provided.", "danger")
        return redirect(request.referrer or url_for('admin_overview'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT tracking_id FROM complaints WHERE id = ?", (id,))
    complaint = cursor.fetchone()

    if not complaint:
        conn.close()
        flash("Complaint not found.", "danger")
        return redirect(url_for('admin_overview'))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        UPDATE complaints
        SET status = ?, admin_notes = ?, updated_at = ?
        WHERE id = ?
    ''', (new_status, admin_notes, now_str, id))

    # Log action
    log_action = f"Status updated to '{new_status}'"
    if admin_notes:
        log_action += f" (Note: {admin_notes})"

    cursor.execute('''
        INSERT INTO activity_logs (complaint_id, action, actor_name)
        VALUES (?, ?, ?)
    ''', (id, log_action, session.get('user_name', 'Admin')))

    conn.commit()
    conn.close()

    flash(f"Complaint #{complaint['tracking_id']} updated to status '{new_status}'.", "success")
    return redirect(request.referrer or url_for('admin_overview'))


@app.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_complaint(id):
    """Delete complaint record."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT tracking_id FROM complaints WHERE id = ?", (id,))
    complaint = cursor.fetchone()

    if complaint:
        cursor.execute("DELETE FROM complaints WHERE id = ?", (id,))
        cursor.execute("DELETE FROM activity_logs WHERE complaint_id = ?", (id,))
        conn.commit()
        flash(f"Complaint #{complaint['tracking_id']} deleted permanently.", "info")
    else:
        flash("Complaint not found.", "danger")

    conn.close()
    return redirect(request.referrer or url_for('admin_overview'))


@app.route('/admin/users')
@admin_required
def admin_users():
    """User Management Page."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.*, COUNT(c.id) as complaint_count
        FROM users u
        LEFT JOIN complaints c ON u.id = c.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin/users.html', users=users)


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Admin Advanced Analytics Page."""
    return render_template('admin/analytics.html')


# -------------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"HTTP 500 Internal Server Error: {e}", exc_info=True)
    return render_template('500.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
