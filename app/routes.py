from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User, Note
from functools import wraps
import os
import uuid
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Admin-only decorator ──────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admins only.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── Home ──────────────────────────────────────────────────────────
@main.route('/')
def home():
    return redirect(url_for('main.login'))

# ── Register ──────────────────────────────────────────────────────
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')
        role     = request.form.get('role', 'user')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.', 'danger')
            return redirect(url_for('main.register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

# ── Login ─────────────────────────────────────────────────────────
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

# ── Logout ────────────────────────────────────────────────────────
@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# ── Dashboard ─────────────────────────────────────────────────────
@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        title   = request.form.get('title', 'Untitled')
        content = request.form.get('content')
        image_filename = None

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                unique_name = f"{uuid.uuid4().hex}.{ext}"
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, unique_name))
                image_filename = unique_name

        if content:
            note = Note(
                title=title,
                content=content,
                image_filename=image_filename,
                user_id=current_user.id
            )
            db.session.add(note)
            db.session.commit()
            flash('Note saved!', 'success')

    # Search
    search = request.args.get('search', '').strip()
    if current_user.role == 'admin':
        if search:
            notes = Note.query.filter(
                (Note.title.ilike(f'%{search}%')) |
                (Note.content.ilike(f'%{search}%'))
            ).order_by(Note.created_at.desc()).all()
        else:
            notes = Note.query.order_by(Note.created_at.desc()).all()
    else:
        if search:
            notes = Note.query.filter_by(user_id=current_user.id).filter(
                (Note.title.ilike(f'%{search}%')) |
                (Note.content.ilike(f'%{search}%'))
            ).order_by(Note.created_at.desc()).all()
        else:
            notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.created_at.desc()).all()

    return render_template('dashboard.html', notes=notes, search=search)

# ── Delete Note ───────────────────────────────────────────────────
@main.route('/note/delete/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    # Only owner or admin can delete
    if note.user_id != current_user.id and current_user.role != 'admin':
        flash('Not allowed.', 'danger')
        return redirect(url_for('main.dashboard'))
    # Delete image file if exists
    if note.image_filename:
        image_path = os.path.join(current_app.root_path, 'static', 'uploads', note.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted.', 'success')
    return redirect(url_for('main.dashboard'))

# ── Admin panel ───────────────────────────────────────────────────
@main.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)