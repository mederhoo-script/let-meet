#!/usr/bin/python3

from flask_sqlalchemy import SQLAlchemy
import json
import os
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase


app = Flask(__name__)
"""create app engine with flask class"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:1234@localhost/chat_users'
db = SQLAlchemy(app)
app.secret_key = os.urandom(24)
app.config["SECRET_KEY"] = "mederh"
socketio = SocketIO(app)

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

with app.app_context():
        db.create_all()

rooms = {}

def gen_room():
    """generating room code"""
    while True:
        code = ""
        for i in range(4):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

@app.route("/", methods=["POST", "GET"])
def choose():
    session.clear()
    if request.method == "POST":
        let_connect = request.form.get("let-connect")
        let_chat = request.form.get("let-chat")
        if let_chat:
            return redirect(url_for("home"))
        if let_connect:
            return redirect(url_for("index"))
        
    return render_template("choose.html")

@app.route("/chat", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code= request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="please enter a name.", code=code, name=name)
        
        if join != False and not code:
             return render_template("home.html", error="please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = gen_room()
            # store generated rome code and messages as dict
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        # store room code and name into session
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    # getting room code from session
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    mem = rooms[room]["members"]
    return render_template("room.html", room=room, mem=mem,
                        messages=rooms[room]["messages"]   )

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
	}
    send(content,to=room)
    rooms[room]["messages"].append(content)

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has enter the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")
    
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]['members'] <= 0:
            del rooms[room]
            print(f"room {room} have been deleted")

    send({"name": name, "message": "has left the room"}, to=room)
    

""" this is the ending of let-chat and
let-connect start from here
"""
if not os.path.exists('users.json'):
    # this have only one dict data which is users
    data = {"users": []}
    with open('users.json', 'w') as jfile:
        json.dump(data, jfile)

# Load initial data from JSON file
with open('users.json', 'r') as file:
    data = json.load(file)
    users = data['users']


@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    global users
    # Get form data
    name = request.form['name']
    username = request.form['username']
    password = request.form['password']
    
    # chech if the user already exist
    exist_user = User.query.filter_by(username=username).first()
    if exist_user:
        alrd_exist = (f"{username} already exist")
        return render_template("index.html", alrd_exist=alrd_exist)

    # Create new user object for json file
    json_new_user = {'name': name, 'username': username, 'password': password}
    # Append new user to list of users
    users.append(json_new_user)
    # Save updated data to JSON file

    with open('users.json', 'w') as file:
        json.dump(data, file, indent=4)
    # Create new user for db
    
    new_user = User(name=name, username=username, password=password)
    # Add the new user to the database session
    db.session.add(new_user)
    db.session.commit()
    
    wel_msg = f"welcome {name} please login below"
    session["wel_msg"] = wel_msg
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
                return redirect('/home1')

        else:
            return render_template('login.html',
                                   error='Invalid username or password')
    else:
        if session.get("wel_msg"):
            wel_msg = session['wel_msg']
            return render_template('login.html', wel_msg=wel_msg)
        return render_template('login.html')


@app.route('/home1')
def home1():
    if 'username' in session:
        return render_template('home1.html',
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


        
if __name__ == "__main__":
    socketio.run(app, debug=True)