from flask import Flask, render_template, request, redirect, session, url_for,flash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient('mongodb://localhost:27017/')
db = client['mydatabase']
signup_collection = db['signup']
pets_collection = db['pets']
applications_collection = db['applications']
adoption_requests_collection=db['adoption_requests']

# Define upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Store file path in MongoDB
        pets_collection.insert_one({'filename': filename})

        flash('File uploaded successfully', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid file type', 'error')
        return redirect(request.url)

# Function to check if the filename has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
   # Query three pets from the database
    three_pets = pets_collection.find().limit(3)
    
    return render_template('index.html', three_pets=three_pets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        user = signup_collection.find_one({'username': username, 'password': password})
        
        if user:  # Password verification
            session['username'] = user['username']
            return redirect(url_for('index'))  # Redirect to dashboard
        else:
            return 'Invalid username or password'
    return render_template('login.html')

@app.route('/Sign_up', methods=['GET', 'POST'])
def Sign_up():
    if request.method == "POST":
        fullname = request.form['fullname']
        password = request.form['password']

        # Check if username already exists
        if signup_collection.find_one({'username': fullname}) is None:
            # Insert new user into the database
            signup_collection.insert_one({'username': fullname, 'password': password})
            session['username'] = fullname  # Set session username
            return redirect(url_for('index'))  # Redirect to index.html after signup
        else:
            return 'Username already exists. Please choose another one.'

    return render_template('sign_up.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        
        # Fetch pets associated with the current user
        user_pets = pets_collection.find({'username': username}).limit(3)
        
        return render_template('index.html', username=username, user_pets=user_pets)
    else:
        return redirect(url_for('login'))
        
@app.route('/create_pet', methods=['GET', 'POST'])
def create_pet():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Get the username from the session
        username = session['username']
        
        # Get pet details from the form
        name = request.form['name']
        breed = request.form['breed']
        age = request.form['age']
        description = request.form['description']
        
        # Handle profile picture upload
        profile_picture_path = None
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture and allowed_file(profile_picture.filename):
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                profile_picture.save(profile_picture_path)
        
        # Insert new pet into the database with the associated username and profile picture path
        pets_collection.insert_one({
            'username': username,
            'name': name,
            'breed': breed,
            'age': age,
            'description': description,
            'profile_picture': profile_picture_path
        })
        
        # Redirect to the "My Pets" page after adding the pet
        return redirect(url_for('mypets'))
    
    return render_template('create_pet.html')



@app.route('/mypets')
def mypets():
    if 'username' in session:
        username = session['username']
        
        # Query pets associated with the current user
        user_pets = pets_collection.find({'username': username})
        
        # Pass the pet data to the template
        return render_template('mypets.html', username=username, user_pets=user_pets)
    else:
        return redirect(url_for('login'))
    
@app.route('/remove_pet/<pet_id>', methods=['POST'])
def remove_pet(pet_id):
    if 'username' in session:
        # Get the username from the session
        username = session['username']
        
        # Check if the logged-in user owns the pet
        pet = pets_collection.find_one({'_id': ObjectId(pet_id), 'username': username})
        if pet:
            # Remove the pet from the database
            pets_collection.delete_one({'_id': ObjectId(pet_id)})
            adoption_requests_collection.delete_one({'_id': ObjectId(pet_id)})
            flash('Pet removed successfully!', 'success')
        else:
            flash('You do not have permission to remove this pet.', 'danger')
        
        # Redirect to the My Pets page
        return redirect(url_for('mypets'))
    else:
        # If the user is not logged in, redirect to the login page
        return redirect(url_for('login'))




@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' in session:
        username = session['username']
        user = signup_collection.find_one({'username': username})
        if request.method == 'POST':
            new_password = request.form['password']
            if new_password:
                signup_collection.update_one({'username': username}, {'$set': {'password': new_password}})
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                profile_picture = request.files['profile_picture']
                if profile_picture and allowed_file(profile_picture.filename):
                    filename = secure_filename(profile_picture.filename)
                    profile_picture_path = os.path.join(UPLOAD_FOLDER, filename)
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                    profile_picture.save(profile_picture_path)
                    # Update the user's profile picture path in the database
                    signup_collection.update_one({'username': username}, {'$set': {'profile_picture': profile_picture_path}})
        # Fetch the updated user data from the database
        user = signup_collection.find_one({'username': username})
        return render_template('profile.html', user=user)
    else:
        return redirect(url_for('login'))

# Route for Admin Panel
@app.route('/admin_panel')
def admin_panel():
    
        # Query all pets from the database
        all_pets = pets_collection.find()
        return render_template('admin_panel.html', all_pets=all_pets, request_sent_for_pet=request_sent_for_pet)


# Route for handling adoption requests
@app.route('/handle_request/<pet_id>', methods=['POST'])
def handle_request(pet_id):
    if 'username' in session:
        if request.method == 'POST':
            action = request.form.get('action')
            username = session['username']
            # Query adoption requests for the logged-in user
            latest_adoption_requests = applications_collection.find({'requester_username': username})
            if action == 'approve':
                # Logic for approving the adoption request
                applications_collection.update_one({'pet_id': pet_id, 'status': 'pending'}, {'$set': {'status': 'approved'}})
                flash('Adoption request approved successfully!', 'success')
            elif action == 'deny':
                # Logic for denying the adoption request
                applications_collection.delete_one({'pet_id': pet_id, 'status': 'pending'})
                flash('Adoption request denied and deleted successfully!', 'success')
            else:
                flash('Invalid action.', 'error')
        
        # Fetch the latest adoption requests from the database
        latest_adoption_requests = applications_collection.find({'pet_id': pet_id})
        
        # Pass the latest adoption requests to the template
        return render_template('adoption_requests.html', adoption_requests=latest_adoption_requests)
    
    else:
        return redirect(url_for('login'))





# Route for sending adoption request
@app.route('/send_adoption_request/<pet_id>', methods=['POST'])
def send_adoption_request(pet_id):
    if 'username' in session:
        if request.method == 'POST':
            # Get the username of the user who posted the pet
            pet = pets_collection.find_one({'_id': ObjectId(pet_id)})
            if pet:
                pet_owner_username = pet['username']
                requester_username = session['username']
                # Store adoption request in the database
                applications_collection.insert_one({
                    'pet_id': pet_id,
                    'pet_name': pet['name'],
                    'pet_owner_username': pet_owner_username,
                    'requester_username': requester_username,
                    'status': 'pending'
                })
                flash('Adoption request sent successfully!', 'success')
            else:
                flash('Pet details not found.', 'error')
        return redirect(url_for('admin_panel'))
    else:
        return redirect(url_for('login'))

@app.route('/adoption_requests')
def adoption_requests():
    if 'username' in session:
        username = session['username']
        # Query adoption requests for the logged-in user
        user_adoption_requests = applications_collection.find({'requester_username': username})

        # Pass the adoption requests data to the template
        return render_template('adoption_requests.html', adoption_requests=user_adoption_requests)
    else:
        return redirect(url_for('login'))






# Add this function to your Flask application

# Define the request_sent_for_pet function in your Flask application file

def request_sent_for_pet(pet_id):
    if 'username' in session:
        username = session['username']
        adoption_request = applications_collection.find_one({
            'pet_id': pet_id,
            'requester_username': username
        })
        return adoption_request is not None
    return False




if __name__ == '__main__':
    app.run(debug=True, port=8000)
