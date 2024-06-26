import os

from flask import Flask, request, render_template, redirect, session, flash
from lib.database_connection import get_flask_database_connection
from lib.user import *
from lib.user_repository import *
from lib.space import *
from lib.space_repository import *
from lib.availability import *
from lib.availability_repository import *
from lib.booking import *
from lib.booking_repository import *


# Create a new Flask app
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# == Your Routes Here ==

# GET /index
# Returns the homepage
# Try it: open http://localhost:5001/index


# MANY ROUTES NOT ALLOWING SERVER TO RUN AS IN CONFLICT

app.secret_key = b'secret_key_to_be_changed'


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/index', methods=['POST'])
def signup_user():
    connection = get_flask_database_connection(app)
    user_repository = UserRepository(connection)
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    phone_number = request.form['phone_number']
    if user_repository.find_user_from_email(email):
        error_message = "Email is already in use."
        return render_template('index.html', error_message=error_message)
    if password != confirm_password:
        error_message = "Passwords don't match!"
        return render_template('index.html', error_message=error_message)
    if password == confirm_password:
        user = User(None, email, password, first_name, last_name, phone_number)
        errors = user.generate_errors()
        if errors:
            return render_template('index.html', errors=errors)
        else:
            user_repository.create(user)
            send_confirmation_email(email)
            return redirect('/successful_signup')

@app.route('/successful_signup')
def successful_signup():
    return render_template('confirmation.html')


@app.route('/confirmation', methods=['GET'])
def confirm_email():
    user_email = request.args.get('email')
    if 'resend' in request.args:
        send_confirmation_email(user_email)
        flash('Confirmation email has been resent! Please check your inbox.', 'success')
    return render_template('confirmation.html', email=user_email)


@app.route('/list_space', methods=['GET'])
def list_space_page():
    return render_template('list_space.html')


@app.route('/list_space', methods=['POST'])
def actually_list_space():
    connection = get_flask_database_connection(app)
    space_repository = SpaceRepository(connection)
    availability_repository = AvailabilityRepository(connection)
    name = request.form['name']
    description = request.form['description']
    price_per_night = request.form['price_per_night']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    new_space = Space(None, name, description, price_per_night, session['user_id'])
    space = space_repository.create(new_space)
    new_availability = Availability(start_date, end_date, space.id)
    availability_repository.add_availability(new_availability)
    user_repository = UserRepository(connection)
    user = user_repository.find(session['user_id'])
    fullname = f"{user.first_name} {user.last_name}" 
    return redirect(f"/spaces/{space.id}?fullname={fullname}")  


@app.route("/logout")
def logout():
    session["email"] = None
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if not session:
            return render_template("login.html")
        session.pop('user_fullname', None)
        session['logged_in'] = False
        return render_template('login.html')
    if request.method == 'POST':
        connection = get_flask_database_connection(app)
        user_repository = UserRepository(connection)
        email = request.form['email']
        password = request.form['password']
        user = user_repository.find_user_from_email(email)
        if user and password == user.password:
            session['logged_in'] = True
            session['user_fullname'] = f'{user.first_name} {user.last_name}'
            session['user_id'] = user.id  # Angelica's request
            return redirect('/spaces')
        return 'Invalid username or password'


@app.route('/spaces/<int:id>', methods=['GET'])
def get_space(id):
    connection = get_flask_database_connection(app)
    space_repository = SpaceRepository(connection)
    space = space_repository.find(id)
    user_repository = UserRepository(connection)
    user = user_repository.find(space.user_id)  
    fullname = f"{user.first_name} {user.last_name}" 
    return render_template('/show.html', space=space, fullname=fullname)


@app.route('/spaces', methods=['GET'])
def view_spaces():
    if not session:
        return render_template('login.html')
    if session.get('logged_in'):
        connection = get_flask_database_connection(app)
        space_repository = SpaceRepository(connection)
        availability_repository = AvailabilityRepository(connection)
        spaces = space_repository.all()
        for space in spaces:
            space.availability = availability_repository.find_by_space_id(space.id)
            user_repository = UserRepository(connection)
            user = user_repository.find(space.user_id)
            space.host_name = f"{user.first_name} {user.last_name}"
            fullname = session['user_fullname']
        return render_template('spaces.html', fullname = fullname, spaces=spaces)
    return render_template('login.html')


@app.route('/spaces/<id>', methods=['POST'])
def make_booking(id):
    if not session:
        return render_template('login.html')
    if session.get('logged_in'):
        connection = get_flask_database_connection(app)
        space_repository = SpaceRepository(connection)
        space = space_repository.find(id)
        booking_repository = BookingRepository(connection)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        booking_repository.create(Booking(None, start_date, end_date, session['user_id'], space.id))
        return redirect('/my_bookings')

@app.route('/my_bookings', methods=['GET'])
def view_bookings():
    return render_template('my_bookings.html')

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5001)))
