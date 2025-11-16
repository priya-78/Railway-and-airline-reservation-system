from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import urlsplit
from datetime import datetime, timedelta
from sqlalchemy import or_

from app import app, db
from models import User, Train, Flight, TrainSchedule, FlightSchedule, Booking, Passenger, Station, Airport
from forms import (
    LoginForm, RegistrationForm, SearchForm, BookingForm, PassengerForm,
    TrainScheduleForm, FlightScheduleForm, TrainForm, FlightForm, StationForm, AirportForm
)


# Helper Functions
def is_admin():
    return current_user.is_authenticated and current_user.is_admin


# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# Public Routes
@app.route('/')
def index():
    search_form = SearchForm()
    return render_template('index.html', title='Home', form=search_form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            if user.is_admin:
                next_page = url_for('admin_dashboard')
            else:
                next_page = url_for('index')
        
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)


# Booking Routes
@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    
    if form.validate_on_submit() or request.method == 'GET' and request.args.get('booking_type'):
        booking_type = form.booking_type.data if form.validate_on_submit() else request.args.get('booking_type')
        source = form.source.data if form.validate_on_submit() else request.args.get('source')
        destination = form.destination.data if form.validate_on_submit() else request.args.get('destination')
        departure_date_str = request.args.get('departure_date') if request.method == 'GET' else None
        departure_date = form.departure_date.data if form.validate_on_submit() else datetime.strptime(departure_date_str, '%Y-%m-%d').date() if departure_date_str else None
        travel_class = form.travel_class.data if form.validate_on_submit() else request.args.get('travel_class', 'economy')
        passengers = form.passengers.data if form.validate_on_submit() else int(request.args.get('passengers', 1))

        if booking_type == 'train':
            # Get source and destination stations
            source_stations = Station.query.filter(
                or_(Station.name.ilike(f'%{source}%'), Station.code.ilike(f'%{source}%'), Station.city.ilike(f'%{source}%'))
            ).all()
            
            destination_stations = Station.query.filter(
                or_(Station.name.ilike(f'%{destination}%'), Station.code.ilike(f'%{destination}%'), Station.city.ilike(f'%{destination}%'))
            ).all()
            
            source_station_ids = [station.id for station in source_stations]
            destination_station_ids = [station.id for station in destination_stations]
            
            # Get train schedules
            schedules = TrainSchedule.query.filter(
                TrainSchedule.departure_station_id.in_(source_station_ids),
                TrainSchedule.arrival_station_id.in_(destination_station_ids),
                TrainSchedule.departure_time >= departure_date,
                TrainSchedule.departure_time < departure_date + timedelta(days=1)
            ).all()
            
            return render_template(
                'booking/train_search.html',
                title='Train Search Results',
                schedules=schedules,
                form=form,
                booking_type=booking_type,
                source=source,
                destination=destination,
                departure_date=departure_date,
                travel_class=travel_class,
                passengers=passengers
            )
        else:  # Flight search
            # Get source and destination airports
            source_airports = Airport.query.filter(
                or_(Airport.name.ilike(f'%{source}%'), Airport.code.ilike(f'%{source}%'), Airport.city.ilike(f'%{source}%'))
            ).all()
            
            destination_airports = Airport.query.filter(
                or_(Airport.name.ilike(f'%{destination}%'), Airport.code.ilike(f'%{destination}%'), Airport.city.ilike(f'%{destination}%'))
            ).all()
            
            source_airport_ids = [airport.id for airport in source_airports]
            destination_airport_ids = [airport.id for airport in destination_airports]
            
            # Get flight schedules
            schedules = FlightSchedule.query.filter(
                FlightSchedule.departure_airport_id.in_(source_airport_ids),
                FlightSchedule.arrival_airport_id.in_(destination_airport_ids),
                FlightSchedule.departure_time >= departure_date,
                FlightSchedule.departure_time < departure_date + timedelta(days=1)
            ).all()
            
            return render_template(
                'booking/flight_search.html',
                title='Flight Search Results',
                schedules=schedules,
                form=form,
                booking_type=booking_type,
                source=source,
                destination=destination,
                departure_date=departure_date,
                travel_class=travel_class,
                passengers=passengers
            )
    
    return render_template('booking/search.html', title='Search', form=form)


@app.route('/select-seat', methods=['GET', 'POST'])
@login_required
def select_seat():
    schedule_id = request.args.get('schedule_id')
    booking_type = request.args.get('booking_type')
    travel_class = request.args.get('travel_class')
    passengers = int(request.args.get('passengers', 1))
    
    if not all([schedule_id, booking_type, travel_class]):
        flash('Missing required information for seat selection', 'danger')
        return redirect(url_for('search'))
    
    # Create booking form
    booking_form = BookingForm()
    booking_form.schedule_id.data = schedule_id
    booking_form.booking_type.data = booking_type
    booking_form.travel_class.data = travel_class
    booking_form.passengers.data = passengers
    
    # Create passenger forms
    passenger_forms = []
    for i in range(passengers):
        passenger_forms.append(PassengerForm(prefix=f'passenger_{i}'))
    
    # Get schedule details
    if booking_type == 'train':
        schedule = TrainSchedule.query.get_or_404(schedule_id)
        total_seats = {
            'economy': schedule.train.total_seats_economy,
            'business': schedule.train.total_seats_business,
            'first': schedule.train.total_seats_first
        }
        available_seats = {
            'economy': schedule.available_seats_economy,
            'business': schedule.available_seats_business,
            'first': schedule.available_seats_first
        }
        price = {
            'economy': schedule.economy_price,
            'business': schedule.business_price,
            'first': schedule.first_price
        }
    else:  # Flight
        schedule = FlightSchedule.query.get_or_404(schedule_id)
        total_seats = {
            'economy': schedule.flight.total_seats_economy,
            'business': schedule.flight.total_seats_business,
            'first': schedule.flight.total_seats_first
        }
        available_seats = {
            'economy': schedule.available_seats_economy,
            'business': schedule.available_seats_business,
            'first': schedule.available_seats_first
        }
        price = {
            'economy': schedule.economy_price,
            'business': schedule.business_price,
            'first': schedule.first_price
        }
    
    total_price = price[travel_class] * passengers
    
    return render_template(
        'booking/select_seat.html',
        title='Select Seats',
        schedule=schedule,
        booking_type=booking_type,
        travel_class=travel_class,
        total_seats=total_seats[travel_class],
        available_seats=available_seats[travel_class],
        passengers=passengers,
        passenger_forms=passenger_forms,
        booking_form=booking_form,
        price_per_ticket=price[travel_class],
        total_price=total_price
    )


@app.route('/book', methods=['POST'])
@login_required
def book():
    booking_form = BookingForm()
    
    if booking_form.validate_on_submit():
        schedule_id = booking_form.schedule_id.data
        booking_type = booking_form.booking_type.data
        travel_class = booking_form.travel_class.data
        passengers = int(booking_form.passengers.data)
        
        # Get price information
        if booking_type == 'train':
            schedule = TrainSchedule.query.get_or_404(schedule_id)
            if travel_class == 'economy':
                price = schedule.economy_price
                available_seats = schedule.available_seats_economy
            elif travel_class == 'business':
                price = schedule.business_price
                available_seats = schedule.available_seats_business
            else:  # first class
                price = schedule.first_price
                available_seats = schedule.available_seats_first
        else:  # Flight
            schedule = FlightSchedule.query.get_or_404(schedule_id)
            if travel_class == 'economy':
                price = schedule.economy_price
                available_seats = schedule.available_seats_economy
            elif travel_class == 'business':
                price = schedule.business_price
                available_seats = schedule.available_seats_business
            else:  # first class
                price = schedule.first_price
                available_seats = schedule.available_seats_first
        
        # Check seat availability
        if available_seats < passengers:
            flash(f'Not enough seats available. Only {available_seats} seats left.', 'danger')
            return redirect(url_for('search'))
        
        # Create booking
        total_amount = price * passengers
        booking = Booking(
            user_id=current_user.id,
            booking_type=booking_type,
            schedule_id=schedule_id,
            travel_class=travel_class,
            total_amount=total_amount,
            status='confirmed'
        )
        
        db.session.add(booking)
        db.session.flush()  # Flush to get the booking ID
        
        # Add passengers
        for i in range(passengers):
            passenger_form = PassengerForm(prefix=f'passenger_{i}')
            if passenger_form.validate():
                passenger = Passenger(
                    booking_id=booking.id,
                    first_name=passenger_form.first_name.data,
                    last_name=passenger_form.last_name.data,
                    age=passenger_form.age.data,
                    gender=passenger_form.gender.data,
                    seat_number=passenger_form.seat_number.data,
                    meal_preference=passenger_form.meal_preference.data
                )
                db.session.add(passenger)
        
        # Update available seats
        if booking_type == 'train':
            if travel_class == 'economy':
                schedule.available_seats_economy -= passengers
            elif travel_class == 'business':
                schedule.available_seats_business -= passengers
            else:  # first class
                schedule.available_seats_first -= passengers
        else:  # Flight
            if travel_class == 'economy':
                schedule.available_seats_economy -= passengers
            elif travel_class == 'business':
                schedule.available_seats_business -= passengers
            else:  # first class
                schedule.available_seats_first -= passengers
        
        db.session.commit()
        
        flash('Booking confirmed successfully!', 'success')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    flash('Something went wrong with your booking. Please try again.', 'danger')
    return redirect(url_for('search'))


@app.route('/booking/confirmation/<int:booking_id>')
@login_required
def booking_confirmation(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only view their own bookings
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to view this booking', 'danger')
        return redirect(url_for('index'))
    
    if booking.booking_type == 'train':
        schedule = TrainSchedule.query.get(booking.schedule_id)
    else:  # Flight
        schedule = FlightSchedule.query.get(booking.schedule_id)
    
    return render_template(
        'booking/confirmation.html',
        title='Booking Confirmation',
        booking=booking,
        schedule=schedule
    )


@app.route('/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only cancel their own bookings
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to cancel this booking', 'danger')
        return redirect(url_for('index'))
    
    # Update booking status
    booking.status = 'cancelled'
    
    # Return seats to available pool
    if booking.booking_type == 'train':
        schedule = TrainSchedule.query.get(booking.schedule_id)
        passengers_count = len(booking.passengers)
        
        if booking.travel_class == 'economy':
            schedule.available_seats_economy += passengers_count
        elif booking.travel_class == 'business':
            schedule.available_seats_business += passengers_count
        else:  # first class
            schedule.available_seats_first += passengers_count
    else:  # Flight
        schedule = FlightSchedule.query.get(booking.schedule_id)
        passengers_count = len(booking.passengers)
        
        if booking.travel_class == 'economy':
            schedule.available_seats_economy += passengers_count
        elif booking.travel_class == 'business':
            schedule.available_seats_business += passengers_count
        else:  # first class
            schedule.available_seats_first += passengers_count
    
    db.session.commit()
    
    flash('Booking has been cancelled successfully', 'success')
    return redirect(url_for('booking_history'))


# User Routes
@app.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html', title='Profile')


@app.route('/booking/history')
@login_required
def booking_history():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    
    # Get schedule details for each booking
    booking_details = []
    for booking in bookings:
        if booking.booking_type == 'train':
            schedule = TrainSchedule.query.get(booking.schedule_id)
            details = {
                'booking': booking,
                'schedule': schedule,
                'source': schedule.departure_station.name if schedule else 'Unknown',
                'destination': schedule.arrival_station.name if schedule else 'Unknown',
                'departure_time': schedule.departure_time if schedule else 'Unknown',
                'arrival_time': schedule.arrival_time if schedule else 'Unknown'
            }
        else:  # Flight
            schedule = FlightSchedule.query.get(booking.schedule_id)
            details = {
                'booking': booking,
                'schedule': schedule,
                'source': schedule.departure_airport.name if schedule else 'Unknown',
                'destination': schedule.arrival_airport.name if schedule else 'Unknown',
                'departure_time': schedule.departure_time if schedule else 'Unknown',
                'arrival_time': schedule.arrival_time if schedule else 'Unknown'
            }
        
        booking_details.append(details)
    
    return render_template(
        'user/booking_history.html',
        title='Booking History',
        booking_details=booking_details
    )


@app.route('/admin')
@login_required
def admin_dashboard():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    # Metrics
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    active_bookings = Booking.query.filter_by(status='confirmed').count()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
    train_bookings = Booking.query.filter_by(booking_type='train').count()
    flight_bookings = Booking.query.filter_by(booking_type='flight').count()

    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        title='Admin Dashboard',
        total_users=total_users,
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        cancelled_bookings=cancelled_bookings,
        train_bookings=train_bookings,        
        flight_bookings=flight_bookings,      
        recent_bookings=recent_bookings
    )



@app.route('/admin/trains')
@login_required
def manage_trains():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    trains = Train.query.all()
    return render_template('admin/manage_trains.html', title='Manage Trains', trains=trains)


@app.route('/admin/trains/add', methods=['GET', 'POST'])
@login_required
def add_train():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    form = TrainForm()
    
    if form.validate_on_submit():
        train = Train(
            name=form.name.data,
            number=form.number.data,
            total_seats_economy=form.total_seats_economy.data,
            total_seats_business=form.total_seats_business.data,
            total_seats_first=form.total_seats_first.data
        )
        
        db.session.add(train)
        db.session.commit()
        
        flash('Train added successfully', 'success')
        return redirect(url_for('manage_trains'))
    
    return render_template('admin/train_form.html', title='Add Train', form=form)


@app.route('/admin/trains/edit/<int:train_id>', methods=['GET', 'POST'])
@login_required
def edit_train(train_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    train = Train.query.get_or_404(train_id)
    form = TrainForm(obj=train)
    
    if form.validate_on_submit():
        train.name = form.name.data
        train.number = form.number.data
        train.total_seats_economy = form.total_seats_economy.data
        train.total_seats_business = form.total_seats_business.data
        train.total_seats_first = form.total_seats_first.data
        
        db.session.commit()
        
        flash('Train updated successfully', 'success')
        return redirect(url_for('manage_trains'))
    
    return render_template('admin/train_form.html', title='Edit Train', form=form, train=train)


@app.route('/admin/trains/delete/<int:train_id>', methods=['POST'])
@login_required
def delete_train(train_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    train = Train.query.get_or_404(train_id)
    
    # Check if train has schedules
    if train.schedules:
        flash('Cannot delete train with active schedules', 'danger')
        return redirect(url_for('manage_trains'))
    
    db.session.delete(train)
    db.session.commit()
    
    flash('Train deleted successfully', 'success')
    return redirect(url_for('manage_trains'))


@app.route('/admin/flights')
@login_required
def manage_flights():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    flights = Flight.query.all()
    return render_template('admin/manage_flights.html', title='Manage Flights', flights=flights)


@app.route('/admin/flights/add', methods=['GET', 'POST'])
@login_required
def add_flight():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    form = FlightForm()
    
    if form.validate_on_submit():
        flight = Flight(
            airline=form.airline.data,
            flight_number=form.flight_number.data,
            aircraft_type=form.aircraft_type.data,
            total_seats_economy=form.total_seats_economy.data,
            total_seats_business=form.total_seats_business.data,
            total_seats_first=form.total_seats_first.data
        )
        
        db.session.add(flight)
        db.session.commit()
        
        flash('Flight added successfully', 'success')
        return redirect(url_for('manage_flights'))
    
    return render_template('admin/flight_form.html', title='Add Flight', form=form)


@app.route('/admin/flights/edit/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def edit_flight(flight_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    flight = Flight.query.get_or_404(flight_id)
    form = FlightForm(obj=flight)
    
    if form.validate_on_submit():
        flight.airline = form.airline.data
        flight.flight_number = form.flight_number.data
        flight.aircraft_type = form.aircraft_type.data
        flight.total_seats_economy = form.total_seats_economy.data
        flight.total_seats_business = form.total_seats_business.data
        flight.total_seats_first = form.total_seats_first.data
        
        db.session.commit()
        
        flash('Flight updated successfully', 'success')
        return redirect(url_for('manage_flights'))
    
    return render_template('admin/flight_form.html', title='Edit Flight', form=form, flight=flight)


@app.route('/admin/flights/delete/<int:flight_id>', methods=['POST'])
@login_required
def delete_flight(flight_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    flight = Flight.query.get_or_404(flight_id)
    
    # Check if flight has schedules
    if flight.schedules:
        flash('Cannot delete flight with active schedules', 'danger')
        return redirect(url_for('manage_flights'))
    
    db.session.delete(flight)
    db.session.commit()
    
    flash('Flight deleted successfully', 'success')
    return redirect(url_for('manage_flights'))


@app.route('/admin/train-schedules')
@login_required
def manage_train_schedules():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    schedules = TrainSchedule.query.all()
    return render_template('admin/manage_train_schedules.html', title='Manage Train Schedules', schedules=schedules)


@app.route('/admin/train-schedules/add', methods=['GET', 'POST'])
@login_required
def add_train_schedule():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    form = TrainScheduleForm()
    
    # Populate select fields
    form.train_id.choices = [(t.id, f"{t.name} ({t.number})") for t in Train.query.all()]
    form.departure_station_id.choices = [(s.id, f"{s.name} ({s.code})") for s in Station.query.all()]
    form.arrival_station_id.choices = [(s.id, f"{s.name} ({s.code})") for s in Station.query.all()]
    
    if form.validate_on_submit():
        train = Train.query.get(form.train_id.data)
        
        schedule = TrainSchedule(
            train_id=form.train_id.data,
            departure_station_id=form.departure_station_id.data,
            arrival_station_id=form.arrival_station_id.data,
            departure_time=form.departure_time.data,
            arrival_time=form.arrival_time.data,
            economy_price=form.economy_price.data,
            business_price=form.business_price.data,
            first_price=form.first_price.data,
            available_seats_economy=train.total_seats_economy,
            available_seats_business=train.total_seats_business,
            available_seats_first=train.total_seats_first
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        flash('Train schedule added successfully', 'success')
        return redirect(url_for('manage_train_schedules'))
    
    return render_template('admin/train_schedule_form.html', title='Add Train Schedule', form=form)

@app.route('/admin/train-schedules/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_train_schedule(schedule_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    schedule = TrainSchedule.query.get_or_404(schedule_id)
    form = TrainScheduleForm(obj=schedule)

    # Populate dropdowns
    form.train_id.choices = [(t.id, f"{t.name} ({t.number})") for t in Train.query.all()]
    form.departure_station_id.choices = [(s.id, f"{s.name} ({s.code})") for s in Station.query.all()]
    form.arrival_station_id.choices = [(s.id, f"{s.name} ({s.code})") for s in Station.query.all()]

    if form.validate_on_submit():
        schedule.train_id = form.train_id.data
        schedule.departure_station_id = form.departure_station_id.data
        schedule.arrival_station_id = form.arrival_station_id.data
        schedule.departure_time = form.departure_time.data
        schedule.arrival_time = form.arrival_time.data
        schedule.economy_price = form.economy_price.data
        schedule.business_price = form.business_price.data
        schedule.first_price = form.first_price.data

        db.session.commit()
        flash('Train schedule updated successfully.', 'success')
        return redirect(url_for('manage_train_schedules'))

    return render_template('admin/train_schedule_form.html', title='Edit Train Schedule', form=form, schedule=schedule)

@app.route('/admin/train-schedules/delete/<int:schedule_id>', methods=['POST'])
@login_required
def delete_train_schedule(schedule_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    schedule = TrainSchedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()

    flash('Train schedule deleted successfully.', 'success')
    return redirect(url_for('manage_train_schedules'))


@app.route('/admin/flight-schedules')
@login_required
def manage_flight_schedules():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    schedules = FlightSchedule.query.all()
    return render_template('admin/manage_flight_schedules.html', title='Manage Flight Schedules', schedules=schedules)


@app.route('/admin/flight-schedules/add', methods=['GET', 'POST'])
@login_required
def add_flight_schedule():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    form = FlightScheduleForm()

    # Populate select fields
    form.flight_id.choices = [(f.id, f"{f.airline} {f.flight_number}") for f in Flight.query.all()]
    form.departure_airport_id.choices = [(a.id, f"{a.name} ({a.code})") for a in Airport.query.all()]
    form.arrival_airport_id.choices = [(a.id, f"{a.name} ({a.code})") for a in Airport.query.all()]

    if form.validate_on_submit():
        flight = Flight.query.get(form.flight_id.data)

        schedule = FlightSchedule(
            flight_id=form.flight_id.data,
            departure_airport_id=form.departure_airport_id.data,
            arrival_airport_id=form.arrival_airport_id.data,
            departure_time=form.departure_time.data,
            arrival_time=form.arrival_time.data,
            economy_price=form.economy_price.data,
            business_price=form.business_price.data,
            first_price=form.first_price.data,
            available_seats_economy=flight.total_seats_economy,
            available_seats_business=flight.total_seats_business,
            available_seats_first=flight.total_seats_first
        )

        db.session.add(schedule)
        db.session.commit()

        flash('Flight schedule added successfully', 'success')
        return redirect(url_for('manage_flight_schedules'))

    return render_template('admin/flight_schedule_form.html', title='Add Flight Schedule', form=form)



@app.route('/admin/stations')
@login_required
def manage_stations():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    stations = Station.query.all()
    return render_template('admin/manage_stations.html', title='Manage Stations', stations=stations)


@app.route('/admin/stations/add', methods=['GET', 'POST'])
@login_required
def add_station():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    form = StationForm()
    
    if form.validate_on_submit():
        station = Station(
            name=form.name.data,
            code=form.code.data,
            city=form.city.data,
            state=form.state.data,
            country=form.country.data
        )
        
        db.session.add(station)
        db.session.commit()
        
        flash('Station added successfully', 'success')
        return redirect(url_for('manage_stations'))
    
    return render_template('admin/station_form.html', title='Add Station', form=form)

@app.route('/admin/stations/edit/<int:station_id>', methods=['GET', 'POST'])
@login_required
def edit_station(station_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    station = Station.query.get_or_404(station_id)
    form = StationForm(obj=station)

    if form.validate_on_submit():
        station.name = form.name.data
        station.code = form.code.data
        station.city = form.city.data
        station.state = form.state.data
        station.country = form.country.data

        db.session.commit()
        flash('Station updated successfully', 'success')
        return redirect(url_for('manage_stations'))

    return render_template('admin/station_form.html', title='Edit Station', form=form, station=station)

@app.route('/admin/stations/delete/<int:station_id>', methods=['POST'])
@login_required
def delete_station(station_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    station = Station.query.get_or_404(station_id)

    # Optional: Add logic to prevent deleting stations linked to schedules
    db.session.delete(station)
    db.session.commit()

    flash('Station deleted successfully', 'success')
    return redirect(url_for('manage_stations'))

@app.route('/admin/flight-schedules/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_flight_schedule(schedule_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    schedule = FlightSchedule.query.get_or_404(schedule_id)
    form = FlightScheduleForm(obj=schedule)

    # Populate select fields
    form.flight_id.choices = [(f.id, f"{f.airline} ({f.flight_number})") for f in Flight.query.all()]
    form.departure_airport_id.choices = [(a.id, f"{a.name} ({a.code})") for a in Airport.query.all()]
    form.arrival_airport_id.choices = [(a.id, f"{a.name} ({a.code})") for a in Airport.query.all()]

    if form.validate_on_submit():
        flight = Flight.query.get(form.flight_id.data)

        schedule.flight_id = form.flight_id.data
        schedule.departure_airport_id = form.departure_airport_id.data
        schedule.arrival_airport_id = form.arrival_airport_id.data
        schedule.departure_time = form.departure_time.data
        schedule.arrival_time = form.arrival_time.data
        schedule.economy_price = form.economy_price.data
        schedule.business_price = form.business_price.data
        schedule.first_price = form.first_price.data
        schedule.available_seats_economy = flight.total_seats_economy
        schedule.available_seats_business = flight.total_seats_business
        schedule.available_seats_first = flight.total_seats_first

        db.session.commit()
        flash('Flight schedule updated successfully', 'success')
        return redirect(url_for('manage_flight_schedules'))

    return render_template('admin/flight_schedule_form.html', title='Edit Flight Schedule', form=form, schedule=schedule)

@app.route('/admin/flight-schedules/delete/<int:schedule_id>', methods=['POST', 'GET'])
@login_required
def delete_flight_schedule(schedule_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    schedule = FlightSchedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash('Flight schedule deleted successfully', 'success')
    return redirect(url_for('manage_flight_schedules'))


@app.route('/admin/airports')
@login_required
def manage_airports():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    airports = Airport.query.all()
    return render_template('admin/manage_airports.html', title='Manage Airports', airports=airports)


@app.route('/admin/airports/add', methods=['GET', 'POST'])
@login_required
def add_airport():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    form = AirportForm()
    
    if form.validate_on_submit():
        airport = Airport(
            name=form.name.data,
            code=form.code.data,
            city=form.city.data,
            state=form.state.data,
            country=form.country.data
        )
        
        db.session.add(airport)
        db.session.commit()
        
        flash('Airport added successfully', 'success')
        return redirect(url_for('manage_airports'))
    
    return render_template('admin/airport_form.html', title='Add Airport', form=form)
@app.route('/admin/airports/edit/<int:airport_id>', methods=['GET', 'POST'])
@login_required
def edit_airport(airport_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    airport = Airport.query.get_or_404(airport_id)
    form = AirportForm(obj=airport)

    if form.validate_on_submit():
        airport.name = form.name.data
        airport.code = form.code.data
        airport.city = form.city.data
        airport.state = form.state.data
        airport.country = form.country.data

        db.session.commit()
        flash('Airport updated successfully', 'success')
        return redirect(url_for('manage_airports'))

    return render_template('admin/airport_form.html', title='Edit Airport', form=form, airport=airport)

@app.route('/admin/airports/delete/<int:airport_id>', methods=['POST'])
@login_required
def delete_airport(airport_id):
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))

    airport = Airport.query.get_or_404(airport_id)

    # Optional safety check: prevent deletion if schedules exist
    if airport.departures or airport.arrivals:
        flash('Cannot delete airport with active schedules', 'danger')
        return redirect(url_for('manage_airports'))

    db.session.delete(airport)
    db.session.commit()

    flash('Airport deleted successfully', 'success')
    return redirect(url_for('manage_airports'))



@app.route('/admin/reports')
@login_required
def admin_reports():
    if not is_admin():
        flash('You do not have permission to access the admin area', 'danger')
        return redirect(url_for('index'))
    
    # Basic reporting
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    
    # Bookings by type
    train_bookings = Booking.query.filter_by(booking_type='train').count()
    flight_bookings = Booking.query.filter_by(booking_type='flight').count()
    
    # Bookings by status
    confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
    
    # Bookings by class
    economy_bookings = Booking.query.filter_by(travel_class='economy').count()
    business_bookings = Booking.query.filter_by(travel_class='business').count()
    first_class_bookings = Booking.query.filter_by(travel_class='first').count()
    
    return render_template(
        'admin/reports.html',
        title='Admin Reports',
        total_users=total_users,
        total_bookings=total_bookings,
        train_bookings=train_bookings,
        flight_bookings=flight_bookings,
        confirmed_bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        economy_bookings=economy_bookings,
        business_bookings=business_bookings,
        first_class_bookings=first_class_bookings
    )
