from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import and_
from sqlalchemy.sql.expression import text

# Import db from app to avoid circular imports
from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    bookings = db.relationship('Booking', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50))
    country = db.Column(db.String(50), nullable=False)
    
    # Relationships
    departures = db.relationship('TrainSchedule', foreign_keys='TrainSchedule.departure_station_id', 
                                backref='departure_station', lazy=True)
    arrivals = db.relationship('TrainSchedule', foreign_keys='TrainSchedule.arrival_station_id', 
                              backref='arrival_station', lazy=True)
    
    def __repr__(self):
        return f'<Station {self.name} ({self.code})>'


class Airport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50))
    country = db.Column(db.String(50), nullable=False)
    
    # Relationships
    departures = db.relationship('FlightSchedule', foreign_keys='FlightSchedule.departure_airport_id', 
                                backref='departure_airport', lazy=True)
    arrivals = db.relationship('FlightSchedule', foreign_keys='FlightSchedule.arrival_airport_id', 
                              backref='arrival_airport', lazy=True)
    
    def __repr__(self):
        return f'<Airport {self.name} ({self.code})>'


class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(20), unique=True, nullable=False)
    total_seats_economy = db.Column(db.Integer, nullable=False)
    total_seats_business = db.Column(db.Integer, nullable=False)
    total_seats_first = db.Column(db.Integer, nullable=False)
    
    # Relationships
    schedules = db.relationship('TrainSchedule', backref='train', lazy=True)
    
    def __repr__(self):
        return f'<Train {self.name} ({self.number})>'


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    airline = db.Column(db.String(100), nullable=False)
    flight_number = db.Column(db.String(20), unique=True, nullable=False)
    aircraft_type = db.Column(db.String(50))
    total_seats_economy = db.Column(db.Integer, nullable=False)
    total_seats_business = db.Column(db.Integer, nullable=False)
    total_seats_first = db.Column(db.Integer, nullable=False)
    
    # Relationships
    schedules = db.relationship('FlightSchedule', backref='flight', lazy=True)
    
    def __repr__(self):
        return f'<Flight {self.airline} {self.flight_number}>'


class TrainSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey('train.id'), nullable=False)
    departure_station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    arrival_station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    economy_price = db.Column(db.Float, nullable=False)
    business_price = db.Column(db.Float, nullable=False)
    first_price = db.Column(db.Float, nullable=False)
    available_seats_economy = db.Column(db.Integer, nullable=False)
    available_seats_business = db.Column(db.Integer, nullable=False)
    available_seats_first = db.Column(db.Integer, nullable=False)
    
    # Relationships
    bookings = db.relationship('Booking', 
                              primaryjoin="and_(Booking.schedule_id==TrainSchedule.id, Booking.booking_type=='train')",
                              foreign_keys="[Booking.schedule_id]",
                              backref='train_schedule', lazy=True)
    
    def __repr__(self):
        return f'<TrainSchedule {self.train.number} {self.departure_station.code} to {self.arrival_station.code}>'


class FlightSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    departure_airport_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    arrival_airport_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    economy_price = db.Column(db.Float, nullable=False)
    business_price = db.Column(db.Float, nullable=False)
    first_price = db.Column(db.Float, nullable=False)
    available_seats_economy = db.Column(db.Integer, nullable=False)
    available_seats_business = db.Column(db.Integer, nullable=False)
    available_seats_first = db.Column(db.Integer, nullable=False)
    
    # Relationships
    bookings = db.relationship('Booking', 
                              primaryjoin="and_(Booking.schedule_id==FlightSchedule.id, Booking.booking_type=='flight')",
                              foreign_keys="[Booking.schedule_id]",
                              backref='flight_schedule', lazy=True)
    
    def __repr__(self):
        return f'<FlightSchedule {self.flight.flight_number} {self.departure_airport.code} to {self.arrival_airport.code}>'


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_type = db.Column(db.String(10), nullable=False)  # 'train' or 'flight'
    schedule_id = db.Column(db.Integer, nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    travel_class = db.Column(db.String(20), nullable=False)  # 'economy', 'business', 'first'
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed')  # 'confirmed', 'cancelled'
    
    # Relationships
    passengers = db.relationship('Passenger', backref='booking', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Booking #{self.id} {self.booking_type} {self.status}>'


class Passenger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10))
    seat_number = db.Column(db.String(10))
    meal_preference = db.Column(db.String(20))  # 'vegetarian', 'non-vegetarian', 'vegan', etc.
    
    def __repr__(self):
        return f'<Passenger {self.first_name} {self.last_name}>'
