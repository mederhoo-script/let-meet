#!/usr/bin/python3
"""app engine"""
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import json
import os

app = Flask(__name__)
"""create app engine with flask class"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
app.secret_key = os.urandom(24)


class User(db.Model):
    """user data to database"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))

    @staticmethod
    def authenticate(username, password):
        """checking if loging details are in database"""
        return User.query.filter_by(username=username,
                                    password=password).first()


if not os.path.exists('users.json'):
    data = {"users": []}
    with open('users.json', 'w') as jfile:
        json.dump(data, jfile)

# Load initial data from JSON file
with open('users.json', 'r') as file:
    data = json.load(file)
    users = data['users']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    global users
    # Get form data
    name = request.form['name']
    username = request.form['username']
    password = request.form['password']
    # Create new user object for json file
    json_new_user = {'name': name, 'username': username, 'password': password}
    # Append new user to list of users
    users.append(json_new_user)
    # Save updated data to JSON file

    with open('users.json', 'w') as file:
        json.dump(data, file, indent=4)
    # Create new user for db
    exist_user = User.query.filter_by(username=username).first()
    if exist_user:
        alrd_exist = (f"{username} already exist")
        return render_template("index.html", alrd_exist=alrd_exist)
    
    new_user = User(name=name, username=username, password=password)
    # Add the new user to the database session
    db.session.add(new_user)
    db.session.commit()

    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Retrieve GPS coordinates from the request
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        # Store coordinates in session or database
        session['latitude'] = latitude
        session['longitude'] = longitude

        user = User.authenticate(username, password)
        if user:
            session['username'] = user.username
            if 'username' in session:
                return redirect('/home')

        else:
            return render_template('login.html',
                                   error='Invalid username or password')
    else:
        return render_template('login.html')


@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html',
                               username=session['username'],
                               latitude=session['latitude'],
                               longitude=session['longitude'])

    else:
        return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')


@app.route('/login/location', methods=['POST', 'GET'])
def login_location():
    data = request.json
    latitude = data['latitude']
    longitude = data['longitude']

    # Process latitude and longitude as needed (e.g., store in database)

    return 'Location received successfully.'


if __name__ == '__main__':
    app.run(debug=True, port=5001)
