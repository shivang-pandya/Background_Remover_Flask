from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo

import random
import string
from PIL import Image
from rembg import remove
import os

# Generate a random 32-character string as the secret key
def generate_secret_key(length=32):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'
app.config['SECRET_KEY'] = generate_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATION']= False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


# Registration Form
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

@app.route("/")
def index():
    return render_template('Project.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('upload_image'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('upload_image'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    
    return render_template('login.html', form=form, is_login=True)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template('login.html', form=form, is_login=False)


# @app.route('/home')
# @login_required
# def home():
#     return f"Hello, {current_user.username}! You are logged in."

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_image():

    if request.method == 'POST':    
        if 'image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file:
            # Save the original image
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(input_path)

            # Process and save the background-removed image
            output_filename = f"no_bg_{file.filename}"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
            
            with Image.open(input_path) as img:
                img = remove(img)
                img.save(output_path, format="PNG")  # Save as PNG to preserve transparency

            # Pass the original and processed image URLs to the template
            original_image_url = url_for('static', filename=f'uploads/{file.filename}')
            processed_image_url = url_for('static', filename=f'processed/{output_filename}')
            return render_template('upload.html', original_image_url=original_image_url, processed_image_url=processed_image_url)
    
    # For GET request, simply render the upload form
    return render_template('upload.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    username = request.form.get('username')
    email = request.form.get('email')

    # Update user's information
    current_user.username = username
    current_user.email = email

    try:
        db.session.commit()
        flash("Profile updated successfully!", "success")
    except:
        db.session.rollback()
        flash("Failed to update profile. Please try again.", "danger")

    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)