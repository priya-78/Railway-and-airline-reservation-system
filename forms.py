from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, IntegerField, FloatField, RadioField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from datetime import datetime
from models import User
from wtforms.fields import DateTimeField
from wtforms import DateTimeField


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class SearchForm(FlaskForm):
    booking_type = RadioField('Booking Type', choices=[('train', 'Train'), ('flight', 'Flight')], default='train', validators=[DataRequired()])
    source = StringField('From', validators=[DataRequired()])
    destination = StringField('To', validators=[DataRequired()])
    departure_date = DateField('Departure Date', format='%Y-%m-%d', validators=[DataRequired()])
    travel_class = SelectField('Class', choices=[('economy', 'Economy'), ('business', 'Business'), ('first', 'First Class')], default='economy')
    passengers = IntegerField('Passengers', default=1, validators=[DataRequired()])
    submit = SubmitField('Search')


class PassengerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[DataRequired()])
    seat_number = StringField('Seat Number')
    meal_preference = SelectField('Meal Preference', choices=[
        ('none', 'No Preference'), 
        ('vegetarian', 'Vegetarian'), 
        ('non-vegetarian', 'Non-Vegetarian'), 
        ('vegan', 'Vegan'),
        ('kosher', 'Kosher'),
        ('halal', 'Halal')
    ])


class BookingForm(FlaskForm):
    schedule_id = HiddenField('Schedule ID', validators=[DataRequired()])
    booking_type = HiddenField('Booking Type', validators=[DataRequired()])
    travel_class = HiddenField('Travel Class', validators=[DataRequired()])
    passengers = HiddenField('Number of Passengers', validators=[DataRequired()])
    submit = SubmitField('Confirm Booking')




class TrainScheduleForm(FlaskForm):
    train_id = SelectField('Train', coerce=int, validators=[DataRequired()])
    departure_station_id = SelectField('Departure Station', coerce=int, validators=[DataRequired()])
    arrival_station_id = SelectField('Arrival Station', coerce=int, validators=[DataRequired()])  # ✅ FIXED

    departure_time = DateTimeField('Departure Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    arrival_time = DateTimeField('Arrival Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])  # ✅ FIXED (single definition)

    economy_price = FloatField('Economy Price', validators=[DataRequired()])
    business_price = FloatField('Business Price', validators=[DataRequired()])
    first_price = FloatField('First Class Price', validators=[DataRequired()])

    submit = SubmitField('Save Schedule')



class FlightScheduleForm(FlaskForm):
    flight_id = SelectField('Flight', coerce=int, validators=[DataRequired()])
    departure_airport_id = SelectField('Departure Airport', coerce=int, validators=[DataRequired()])
    arrival_airport_id = SelectField('Arrival Airport', coerce=int, validators=[DataRequired()])
    departure_time = DateTimeField('Departure Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    arrival_time = DateTimeField('Arrival Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    economy_price = FloatField('Economy Price', validators=[DataRequired()])
    business_price = FloatField('Business Price', validators=[DataRequired()])
    first_price = FloatField('First Class Price', validators=[DataRequired()])
    submit = SubmitField('Save Schedule')


class TrainForm(FlaskForm):
    name = StringField('Train Name', validators=[DataRequired()])
    number = StringField('Train Number', validators=[DataRequired()])
    total_seats_economy = IntegerField('Economy Seats', validators=[DataRequired()])
    total_seats_business = IntegerField('Business Seats', validators=[DataRequired()])
    total_seats_first = IntegerField('First Class Seats', validators=[DataRequired()])
    submit = SubmitField('Save Train')


class FlightForm(FlaskForm):
    airline = StringField('Airline', validators=[DataRequired()])
    flight_number = StringField('Flight Number', validators=[DataRequired()])
    aircraft_type = StringField('Aircraft Type', validators=[DataRequired()])
    total_seats_economy = IntegerField('Economy Seats', validators=[DataRequired()])
    total_seats_business = IntegerField('Business Seats', validators=[DataRequired()])
    total_seats_first = IntegerField('First Class Seats', validators=[DataRequired()])
    submit = SubmitField('Save Flight')


class StationForm(FlaskForm):
    name = StringField('Station Name', validators=[DataRequired()])
    code = StringField('Station Code', validators=[DataRequired(), Length(min=2, max=10)])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State')
    country = StringField('Country', validators=[DataRequired()])
    submit = SubmitField('Save Station')


class AirportForm(FlaskForm):
    name = StringField('Airport Name', validators=[DataRequired()])
    code = StringField('Airport Code', validators=[DataRequired(), Length(min=3, max=3)])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State')
    country = StringField('Country', validators=[DataRequired()])
    submit = SubmitField('Save Airport')
