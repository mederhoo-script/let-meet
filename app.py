#!/usr/bin/python3

from flask_sqlalchemy import SQLAlchemy
import json
import os
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
from flask_login import current_user, login_required, LoginManager, UserMixin
from flask_migrate import Migrate # type: ignore
from werkzeug.utils import secure_filename
from PIL import Image
import uuid


app = Flask(__name__)
"""create app engine with flask class"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:1234@localhost/chat_users'
db = SQLAlchemy(app)
app.secret_key = os.urandom(24)
app.config["SECRET_KEY"] = "mederh"
socketio = SocketIO(app)
migrate = Migrate(app, db)



class User(db.Model):
    """user data to database"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(255), default="")  # Path to the profile picture
    story_pic = db.Column(db.String(255), default="")
    posts = db.relationship('Post', backref='author', lazy=True)

    @staticmethod
    def authenticate(username, password):
        """checking if loging details are in database"""
        return User.query.filter_by(username=username,
                                    password=password).first()
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feed_pic = db.Column(db.String(255), default="")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return '<Post %r>' % self.content


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
    email = request.form.get('email')
    
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
    new_user = User(name=name, username=username, password=password, email=email)
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


@app.route('/home1', methods=['POST', 'GET'])
def home1():
    if 'username' in session:
        user = User.query.filter_by(username=session.get('username')).first()
        full_name = user.name
        session['user_id'] = user.id
        if user:
            user_id = user.id
            session['user_id'] = user.id
        post = Post.query.filter_by(user_id=session['user_id']).all()
        username = session['username']
        profile_pic = user.profile_pic
        story_pic = user.story_pic
        contents = []
        if post:
            for i in post:
                content = i.feed_pic
                content = eval(content)
                contents.append(content)
                contents.reverse()

        return render_template('home1.html',
                               username=username,
                               latitude=session['latitude'],
                               longitude=session['longitude'],
                               post=post,
                               full_name=full_name,
                               profile_pic=profile_pic,
                               story_pic=story_pic, contents=contents)

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

@app.route('/post_message', methods=['POST', 'GET'])
def post_message():
    user_id = None
    message = ""
    image_path = request.form.get('image_path')  # Assuming 'image_path' is the name of the form field for the image path
    user_id = request.form.get('user_id')  # Assuming 'user_id' is the name of the form field for the user ID

    
    if 'message' in request.form:  # Text post
        message = request.form['message'].strip()  # Strip leading/trailing whitespace
        if not message:  # If message is empty
            flash('Please enter some text for your post', 'error')
            return redirect(url_for('home1'))
        
        user = User.query.filter_by(username=session.get('username')).first()
        if user:
            user_id = user.id
    elif 'image' in request.files:  # Image post
        image = request.files['image']
        if image.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('static/uploads', filename)

            # Create the 'uploads' directory if it doesn't exist
            os.makedirs('static/uploads', exist_ok=True)

            # Save the uploaded image to the 'uploads' directory
            image.save(image_path)

            # Resize the image to a specific size (e.g., 300x300)
            img = Image.open(image_path)
            img.thumbnail((300, 300))  # Resize the image to fit within a 300x300 box
            img.save(image_path)  # Save the resized image


            image_path = os.path.join('uploads', filename)

            user = User.query.filter_by(username=session.get('username')).first()
            if user:
                user_id = user.id
    else:  # If neither message nor image is provided
        flash('Please provide content for your post', 'error')
        return redirect(url_for('home1'))
    
    if user_id is not None:  # Check if user_id has been assigned a value
        new_post = Post(content=message if 'message' in locals() else None,
                        image_path=image_path if 'image_path' in locals() else None,
                        user_id=user_id)
        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully', 'success')
    
    return redirect(url_for('home1'))

# Route to handle the profile picture upload
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('home1'))
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(url_for('home1'))
    
    # Save the file to a location on the server
    filename = secure_filename(file.filename)
    file_path = os.path.join('static/uploads/profile_pictures', filename)
    os.makedirs('static/uploads/profile_pictures', exist_ok=True)
    file.save(file_path)

    # Resize the image to a specific size (e.g., 300x300)
    img = Image.open(file_path)
    img.thumbnail((150, 150))  # Resize the image to fit within a 300x300 box
    img.save(file_path)  # Save the resized image


    file_path = os.path.join('uploads/profile_pictures', filename)
    
    # Update the user's profile picture path in the database
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.profile_pic = file_path
            db.session.commit()
            flash('Profile picture updated successfully', 'success')
        else:
            flash('User not found', 'error')
    else:
        flash('User not logged in', 'error')
    
    return redirect(url_for('home1'))


# Route to handle the story
@app.route('/story_pic', methods=['POST'])
def story_pic():
    if 'file' not in request.files:
        return redirect(url_for('home1'))
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(url_for('home1'))
    
    # Save the file to a location on the server
    filename = secure_filename(file.filename)
    file_path = os.path.join('static/uploads/story_pictures', filename)
    os.makedirs('static/uploads/story_pictures', exist_ok=True)
    file.save(file_path)

    # Resize the image to a specific size (e.g., 300x300)
    img = Image.open(file_path)
    img.thumbnail((200, 340))  # Resize the image to fit within a 200x340 box
    img.save(file_path)  # Save the resized image

    file_path = os.path.join('uploads/story_pictures', filename)
    
    # Update the user's profile picture path in the database
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.story_pic = file_path
            db.session.commit()
            flash('Profile picture updated successfully', 'success')
        else:
            flash('User not found', 'error')
    else:
        flash('User not logged in', 'error')
    
    return redirect(url_for('home1'))


# Route to handle the feeds post
@app.route('/feed_pic', methods=['POST'])
def feed_pic():
    text = ''
    file_path = ''
    contents = {}

    text = request.form['text']
    file = request.files['file']

    if file.filename == '' and text == '':
        return redirect(url_for('home1'))
    
    if file:
        # Save the file to a location on the server
        filename = secure_filename(str(uuid.uuid4()) + file.filename)
        file_path = os.path.join('static/uploads/feed_pictures', filename)
        os.makedirs('static/uploads/feed_pictures', exist_ok=True)
        file.save(file_path)

        # Resize the image to a specific size (e.g., 300x300)
        img = Image.open(file_path)
        img.thumbnail((1000, 620))  # Resize the image to fit within a 1000x620 box
        img.save(file_path)  # Save the resized image


        file_path = os.path.join('uploads/feed_pictures', filename)
    
    contents[file_path] = text

    # Update the user's feed picture path in the database
    if 'username' in session:
        #user = User.query.filter_by(username=session['username']).first()
        #if user:
    #        user.feed_pic = contents
    #        db.session.commit()
    #        flash('Profile picture updated successfully', 'success')
    #    else:
    #        flash('User not found', 'error')
    #else:
    #    flash('User not logged in', 'error')


        user = User.query.filter_by(username=session.get('username')).first()
        if user:
            user_id = user.id
       
        if user_id is not None:  # Check if user_id has been assigned a value
            new_post = Post(feed_pic=contents,
                            user_id=user_id)
            db.session.add(new_post)
            db.session.commit()

    return redirect(url_for('home1'))



        
if __name__ == "__main__":
    socketio.run(app, debug=True)