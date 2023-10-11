import datetime
import os
import urllib
from statistics import mean, median

import flask_login
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, send_file, url_for, make_response, jsonify, flash
from flask_bcrypt import check_password_hash
from flask_wtf import FlaskForm
from sqlalchemy import create_engine, Column, Integer, ForeignKey, Numeric, Date, extract, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from wtforms import StringField, PasswordField, DateField, DecimalField
from wtforms.validators import InputRequired, Length, Optional, NumberRange

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["REMEMBER_COOKIE_SAMESITE"] = "Strict"
app.config["WTF_CSRF_SECRET_KEY"] = os.getenv('WTF_CSRF_SECRET_KEY')
login_manager = flask_login.LoginManager()
login_manager.session_protection = "strong"
login_manager.init_app(app)

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

if app.debug:
    engine = create_engine('sqlite:///fuel.db', echo=True)
else:
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_DATABASE = os.getenv('DB_DATABASE')
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?charset=utf8mb4")


Base = declarative_base()


class Car(Base):
    __tablename__ = 'Car'
    car_id = Column(Integer, primary_key=True)
    make = Column(Text)
    model = Column(Text)
    year = Column(Integer)
    buy_cost = Column(Numeric(10, 2))
    buy_kmstand = Column(Numeric(10, 2))
    consumption_green = Column(Numeric(3, 2))
    consumption_red = Column(Numeric(3, 2))
    fill_ups = relationship('FillUp', back_populates='car')
    taxes = relationship('CarTax', back_populates='car')
    insurance = relationship('CarInsurance', back_populates='car')
    repairs = relationship('CarRepair', back_populates='car')
    repair_exists = relationship('RepairExist', back_populates='car')
    repair_done = relationship('RepairDone', back_populates='car')
    users = relationship('UserCar', back_populates='car')


class FillUp(Base):
    __tablename__ = 'FillUp'
    fill_up_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    gallons = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))
    date = Column(Date)
    drived_meters = Column(Numeric(10, 2))
    car = relationship('Car', back_populates='fill_ups')


class CarTax(Base):
    __tablename__ = 'CarTax'
    car_tax_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    cost = Column(Numeric(10, 2))
    date = Column(Date)
    description = Column(Text)
    car = relationship('Car', back_populates='taxes')


class CarInsurance(Base):
    __tablename__ = 'CarInsurance'
    car_insurance_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    description = Column(Text)
    date = Column(Date)
    cost = Column(Numeric(10, 2))
    car = relationship('Car', back_populates='insurance')


class CarRepair(Base):
    __tablename__ = 'CarRepair'
    car_repair_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    description = Column(Text)
    firma = Column(Text)
    cost = Column(Numeric(10, 2))
    kmstand = Column(Numeric(10, 2))
    date = Column(Date)
    car = relationship('Car', back_populates='repairs')


class RepairExist(Base):
    __tablename__ = 'RepairExist'
    car_repair_exist_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    name = Column(Text)
    intervall = Column(Text)
    car = relationship('Car', back_populates='repair_exists')
    repair_done = relationship('RepairDone', back_populates='repair_exists')


class RepairDone(Base):
    __tablename__ = 'RepairDone'
    car_repair_done_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    car_repair_exist_id = Column(Integer, ForeignKey('RepairExist.car_repair_exist_id'))
    description = Column(Text)
    begin_date = Column(Date)
    begin_kmstand = Column(Numeric(10, 2))
    end_kmstand = Column(Numeric(10, 2))
    end_date = Column(Date)
    repair_exists = relationship('RepairExist', back_populates='repair_done')
    car = relationship('Car', back_populates='repair_done')


class UserCar(Base):
    __tablename__ = 'UserCar'
    user_car_id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('Car.car_id'))
    name = Column(Text)
    car = relationship('Car', back_populates='users')


Base.metadata.create_all(engine)  # Create the database tables


class User(flask_login.UserMixin):
    pass


users = {'replace_user1': {'password': 'replace_password1'}}


@login_manager.user_loader
def user_loader(user_name):
    if user_name not in users:
        return

    user = User()
    user.id = user_name
    return user


@login_manager.request_loader
def request_loader(request):
    user_name = request.form.get('user_name')
    if user_name not in users:
        return

    user = User()
    user.id = user_name
    return user


class login_form(FlaskForm):
    user_name = StringField(validators=[InputRequired(), Length(1, 64)])
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=72)])


def redirect_to(redirect):
    if redirect in [url_for("index"), url_for("tanken"), url_for('grafik'), url_for('kostenubersicht'),
                    url_for('steuer'), url_for('wartungsintervall'),
                    url_for('versicherung'), url_for('neue_versicherung'),
                    url_for('new_car'), url_for('select_car'),
                    url_for('change_car'), url_for('neue_wartung'),
                    url_for('wartung'), url_for('neue_steuer'),
                    url_for('neuer_fillup')]:
        return redirect
    else:
        return url_for("tanken")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = login_form()

    if form.validate_on_submit():
        try:
            user_name = form.user_name.data
            entered_password = form.password.data
            if user_name in users and check_password_hash(users[user_name]['password'], entered_password):
                user = User()
                user.id = user_name
                flask_login.login_user(user=user, remember=True, duration=datetime.timedelta(weeks=4))

                next_redirect = redirect_to(request.args.get('next_redirect'))
                return redirect(next_redirect)

            flash("Login fehlgeschlagen!", "danger")
        except Exception as e:
            # flash(e, "danger") # dont expose error messages
            flash("Login fehlgeschlagen!", "danger")

    if flask_login.current_user.is_authenticated:
        next_redirect = redirect_to(request.args.get('next_redirect'))
        return redirect(next_redirect)

    return render_template("auth.html",
                           form=form,
                           text="Anmelden",
                           title="Anmelden",
                           btn_action="Anmelden")


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('login'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    # return 'Unauthorized', 401
    # sleep(1)
    # return render_template('login.html', next_redirect=request.path)
    return redirect(url_for('login') + f"?next_redirect={urllib.parse.quote(request.path)}")
    # return redirect(url_for('login' + f"?next_redirect={urllib.parse.quote(request.path)}"))


@app.errorhandler(404)
def handle_404(e):
    # handle all other routes here
    return redirect(url_for('login') + f"?next_redirect={urllib.parse.quote(request.path)}")
    # return render_template('login.html', next_redirect=request.path)


@app.after_request
def apply_caching(response):
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def get_price_per_liter(costs, liters):
    return round((costs / liters), 2)


def get_consumption_per_100_km(liters, drived_kilometers):
    consm = (liters * 100) / drived_kilometers
    return round(consm, 2)


def valid_car(car_id) -> bool:
    if not car_id:
        # when no cookie is set
        return False

    try:
        car_id = int(car_id)
    except ValueError:
        # when id is no int
        return False

    Session = sessionmaker(bind=engine)
    session = Session()

    car = session.query(Car).join(UserCar).filter_by(name=flask_login.current_user.id).filter(
        Car.car_id == car_id).first()
    # car = session.query(Car).filter(Car.car_id == car_id).first()
    if not car:
        # if car does not exist (yet)
        session.close()
        return False
    session.close()

    return True


@app.route('/tanken', methods=['GET'])
@flask_login.login_required
def tanken():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    # create session and query fill-up data with car and fuel information
    Session = sessionmaker(bind=engine)
    session = Session()

    buy_kmstand = session.query(Car).filter(Car.car_id == car_id).scalar().buy_kmstand
    fill_ups = session.query(FillUp).filter(FillUp.car_id == car_id).order_by(FillUp.fill_up_id.desc()).all()
    if len(fill_ups) > 0:
        # total_kilometers = session.query(func.sum(FillUp.drived_meters)).scalar()
        # print(f"sqlalchemy calculated total_kilometers: {total_kilometers}")
        total_kilometers = sum([fill_up.drived_meters for fill_up in fill_ups]) + buy_kmstand
        # print(f"python.... calculated total_kilometers: {total_kilometers}")

        # total_costs = session.query(func.sum(FillUp.total_cost)).scalar()
        # print(f"sqlalchemy calculated total_costs: {total_costs}")
        total_costs = sum([fill_up.total_cost for fill_up in fill_ups])
        # print(f"python.... calculated total_costs: {total_costs}")

        # av_consumption = session.query(func.avg(FillUp.consumption_per_100km)).scalar()
        # if av_consumption:
        #     av_consumption = round(av_consumption, 2)
        # av_100km = session.query(func.avg(FillUp.price_per_100km)).scalar()
        # if av_100km:
        #     av_100km = round(av_100km, 2)
        # print(f"sqlalchemy calculated: {av_100km}")

        # av_price_per_liter = session.query(func.avg(FillUp.total_cost / FillUp.gallons)).scalar()
        # if av_price_per_liter:
        #     av_price_per_liter = round(av_price_per_liter, 2)
        #     print(f"sqlalchemy calculated av_price_per_liter: {av_price_per_liter}")

        drived_kilometers = buy_kmstand
        for fill_up in fill_ups:
            fill_up.price_per_gallon = get_price_per_liter(fill_up.total_cost, fill_up.gallons)

            if fill_up.drived_meters:
                fill_up.consumption_per_100km = get_consumption_per_100_km(fill_up.gallons, fill_up.drived_meters)
            else:
                fill_up.consumption_per_100km = get_consumption_per_100_km(fill_up.gallons, 1)

            fill_up.price_per_100km = round((fill_up.consumption_per_100km * fill_up.price_per_gallon), 2)
            drived_kilometers += fill_up.drived_meters
            fill_up.kilometers_after_fillup = drived_kilometers

        av_price_per_liter = round(mean([fill_up.price_per_gallon for fill_up in fill_ups]), 2)
        # print(f"python calculated av_price_per_liter: {av_price_per_liter}")

        total_liters = round(sum([fill_up.gallons for fill_up in fill_ups]), 2)
        own_kilometers = round(sum([fill_up.drived_meters for fill_up in fill_ups]), 2)
        gesamt_average_consumption_per_100km = None  # todo: auskommentiert in html
        # gesamt_average_consumption_per_100km = round(((total_liters * 100) / own_kilometers),2)  # todo: auskommentiert in html

        av_price_per_100km = round(mean([fill_up.price_per_100km for fill_up in fill_ups]), 2)
        # print(f"python calculated av_price_per_100km: {av_price_per_100km}")

        av_consumption_per_100km = round(mean([fill_up.consumption_per_100km for fill_up in fill_ups]), 2)
        # print(f"python calculated av_consumption_per_100km: {av_consumption_per_100km}")

        median_consumption = round(median([fill_up.consumption_per_100km for fill_up in fill_ups]), 2)
    else:
        total_liters = None
        av_consumption_per_100km = None
        median_consumption = None
        av_price_per_100km = None
        total_costs = None
        total_kilometers = None
        av_price_per_liter = None
        own_kilometers = None
        gesamt_average_consumption_per_100km = None

    # kilometers_after_fillup = Column(Numeric(10, 2))
    # price_per_gallon = Column(Numeric(10, 2))
    # price_per_100km = Column(Numeric(10, 2))
    # consumption_per_100km = Column(Numeric(10, 2))
    #
    # print(type(av_consumption))
    # print(type(total_kilometers))
    # pass fill-up data to the template
    session.close()

    session = Session()
    car = session.query(Car).filter(Car.car_id == car_id).scalar()
    if car.consumption_red:
        consumption_red = car.consumption_red
    else:
        consumption_red = 5.5
    if car.consumption_green:
        consumption_green = car.consumption_green
    else:
        consumption_green = 5
    session.close()
    return render_template('fill_ups.html', fill_ups=fill_ups, total_kilometers=total_kilometers,
                           total_liters=total_liters,
                           total_costs=total_costs, av_price_per_liter=av_price_per_liter,
                           av_consumption=av_consumption_per_100km, median_consumption=median_consumption,
                           av_price_per_100km=av_price_per_100km,
                           own_kilometers=own_kilometers,
                           gesamt_average_consumption_per_100km=gesamt_average_consumption_per_100km,
                           consumption_red=consumption_red, consumption_green=consumption_green, title="Tanken")


@app.route('/', methods=['GET'])
@flask_login.login_required
def index():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    # create session and query fill-up data with car and fuel information
    Session = sessionmaker(bind=engine)
    session = Session()

    fill_ups = session.query(FillUp).filter(FillUp.car_id == car_id).order_by(FillUp.fill_up_id.desc()).limit(5).all()
    for fill_up in fill_ups:
        fill_up.price_per_gallon = get_price_per_liter(fill_up.total_cost, fill_up.gallons)

        if fill_up.drived_meters:
            fill_up.consumption_per_100km = get_consumption_per_100_km(fill_up.gallons, fill_up.drived_meters)
        else:
            fill_up.consumption_per_100km = get_consumption_per_100_km(fill_up.gallons, 1)

        fill_up.price_per_100km = round((fill_up.consumption_per_100km * fill_up.price_per_gallon), 2)

    session.close()

    session = Session()
    car = session.query(Car).filter(Car.car_id == car_id).scalar()
    if car.consumption_red:
        consumption_red = car.consumption_red
    else:
        consumption_red = 5.5
    if car.consumption_green:
        consumption_green = car.consumption_green
    else:
        consumption_green = 5
    session.close()

    return render_template('index.html', fill_ups=fill_ups, consumption_green=consumption_green,
                           consumption_red=consumption_red, title="Übersicht")


@app.route('/grafik')
@app.route('/grafik/<selected_year>')
@flask_login.login_required
def grafik(selected_year=None):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    if selected_year:
        try:
            selected_year = int(selected_year)
        except ValueError:
            return "falscher Wert Jahr", 400

    fillup_year_data = session.query(FillUp.date).filter(FillUp.car_id == car_id).group_by(FillUp.date).all()
    available_years = set()
    for year in fillup_year_data:
        available_years.add(year.date.year)
    available_years = sorted(available_years)
    session.close()

    return render_template('grafik.html', selected_year=selected_year, available_years=available_years,
                           title="Grafiken")


@app.route('/chart/<type_data>')
@flask_login.login_required
def chart(type_data):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    year = request.args.get('year')
    if type_data == 'sprit':
        Session = sessionmaker(bind=engine)
        session = Session()

        if year:
            fillups = session.query(FillUp).filter(FillUp.car_id == car_id).filter(
                extract('year', FillUp.date) == year).all()
        else:
            fillups = session.query(FillUp).filter(FillUp.car_id == car_id).all()
        data = []
        for fillup in fillups:
            consumption = get_price_per_liter(fillup.total_cost, fillup.gallons)
            data.append({'date': fillup.date.strftime('%Y-%m-%d'), 'value': consumption})
        session.close()
        return jsonify(data)
    elif type_data == 'verbrauch':
        Session = sessionmaker(bind=engine)
        session = Session()

        if year:
            fillups = session.query(FillUp).filter(FillUp.car_id == car_id).filter(
                extract('year', FillUp.date) == year).all()
        else:
            fillups = session.query(FillUp).filter(FillUp.car_id == car_id).all()
        data = []
        for fillup in fillups:
            consumption = get_consumption_per_100_km(fillup.gallons, fillup.drived_meters)
            data.append({'date': fillup.date.strftime('%Y-%m-%d'), 'value': consumption})
        session.close()
        return jsonify(data)
    # elif type_data == 'kosten':
    #     Session = sessionmaker(bind=engine)
    #     session = Session()
    #
    #     fillup_year_data = session.query(FillUp.date).filter(FillUp.car_id == car_id).group_by(FillUp.date).all()
    #     fillup_years = set()
    #     for year in fillup_year_data:
    #         fillup_years.add(year.date.year)
    #
    #     data = []
    #     set_year_data = {}
    #     for year in fillup_years:
    #         if year not in set_year_data:
    #             set_year_data[year] = {}
    #         if session.query(Car).count() == 0:
    #             session.close()
    #             return redirect(url_for('new_car') + "#car_missing")
    #         fillup_data_for_year = session.query(FillUp).filter(FillUp.car_id == car_id).filter(
    #             extract('year', FillUp.date) == year).all()
    #         drived_meters = sum([fill_up.drived_meters for fill_up in fillup_data_for_year])
    #
    #         set_year_data[year]["drived_meters"] = drived_meters
    #         data.append({'date': str(year), 'value': drived_meters})
    #
    #     session.close()
    #     return jsonify(data)


@app.route('/kostenubersicht')
@flask_login.login_required
def kostenubersicht():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    fillup_year_data = session.query(FillUp.date).filter(FillUp.car_id == car_id).group_by(FillUp.date).all()
    fillup_years = set()
    for year in fillup_year_data:
        fillup_years.add(year.date.year)

    set_year_data = {}
    for year in fillup_years:
        if year not in set_year_data:
            set_year_data[year] = {}
        if session.query(Car).count() == 0:
            session.close()
            return redirect(url_for('new_car') + "#car_missing")
        car_id = request.cookies.get('car_id')
        if not car_id:
            car_id = session.query(Car).first().car_id
        try:
            car_id = int(car_id)
        except ValueError:
            session.close()
            return "falscher Wert Cookie", 400
        car = session.query(Car).filter(Car.car_id == car_id).first()
        if not car:
            session.close()
            return redirect(url_for('new_car') + "#car_missing")
        fillup_data_for_year = session.query(FillUp).filter(FillUp.car_id == car_id).filter(
            extract('year', FillUp.date) == year).all()
        tankkosten = sum([fill_up.total_cost for fill_up in fillup_data_for_year])
        drived_meters = sum([fill_up.drived_meters for fill_up in fillup_data_for_year])

        set_year_data[year]["tankcost"] = tankkosten
        set_year_data[year]["drived_meters"] = drived_meters

    insurance_year_data = session.query(CarInsurance.date).filter(CarInsurance.car_id == car_id).group_by(
        CarInsurance.date).all()
    insurance_years = set()
    for year in insurance_year_data:
        insurance_years.add(year.date.year)

    for year in insurance_years:
        if year not in set_year_data:
            set_year_data[year] = {}

        insurance_data_for_year = session.query(CarInsurance).filter(CarInsurance.car_id == car_id).filter(
            extract('year', CarInsurance.date) == year).all()
        insurance = sum([insurance.cost for insurance in insurance_data_for_year])

        set_year_data[year]["insurance"] = insurance

    tax_year_data = session.query(CarTax.date).filter(CarTax.car_id == car_id).group_by(
        CarTax.date).all()
    tax_years = set()
    for year in tax_year_data:
        tax_years.add(year.date.year)

    for year in tax_years:
        if year not in set_year_data:
            set_year_data[year] = {}

        tax_data_for_year = session.query(CarTax).filter(CarTax.car_id == car_id).filter(
            extract('year', CarTax.date) == year).all()
        tax = sum([tax.cost for tax in tax_data_for_year])

        set_year_data[year]["tax"] = tax

    repair_year_data = session.query(CarRepair.date).filter(CarRepair.car_id == car_id).group_by(
        CarRepair.date).all()
    repair_years = set()
    for year in repair_year_data:
        repair_years.add(year.date.year)

    for year in repair_years:
        if year not in set_year_data:
            set_year_data[year] = {}

        repair_data_for_year = session.query(CarRepair).filter(CarRepair.car_id == car_id).filter(
            extract('year', CarRepair.date) == year).all()
        repair = sum([repair.cost for repair in repair_data_for_year])

        set_year_data[year]["repair"] = repair

    print(set_year_data)
    sorted_years = sorted(set_year_data)
    list_table_data = []
    for year in sorted_years:
        tankcost = set_year_data[year]["tankcost"] if "tankcost" in set_year_data[year] else 0
        drived_meters = set_year_data[year]["drived_meters"] if "drived_meters" in set_year_data[year] else 0
        insurance = set_year_data[year]["insurance"] if "insurance" in set_year_data[year] else 0
        tax = set_year_data[year]["tax"] if "tax" in set_year_data[year] else 0
        repair = set_year_data[year]["repair"] if "repair" in set_year_data[year] else 0
        costs = insurance + tankcost + tax + repair
        costs_per_kilometer = round((costs / drived_meters), 2) if drived_meters > 0 else "---"
        list_table_data.append({"year": year, "tankcost": tankcost,
                                "drived_meters": drived_meters,
                                "insurance": insurance,
                                "tax": tax,
                                "repair": repair,
                                "costs": costs,
                                "costs_per_kilometer": costs_per_kilometer * 100})

    gesamt_drived_kilometers = sum([year["drived_meters"] for year in list_table_data])
    gesamt_insurance = sum([year["insurance"] for year in list_table_data])
    gesamt_tax = sum([year["tax"] for year in list_table_data])
    gesamt_repair = sum([year["repair"] for year in list_table_data])
    gesamt_tank_cost = sum([year["tankcost"] for year in list_table_data])

    if session.query(Car).count() == 0:
        session.close()
        return redirect(url_for('new_car') + "#car_missing")
    car_id = request.cookies.get('car_id')
    if not car_id:
        car_id = session.query(Car).first().car_id
    try:
        car_id = int(car_id)
    except ValueError:
        session.close()
        return "falscher Wert Cookie", 400
    car = session.query(Car).filter(Car.car_id == car_id).first()
    if not car:
        session.close()
        return redirect(url_for('new_car') + "#car_missing")

    buy_cost = session.query(Car).filter(Car.car_id == car_id).scalar().buy_cost
    buy_kmstand = session.query(Car).filter(Car.car_id == car_id).scalar().buy_kmstand

    fill_up_first = session.query(FillUp).filter(FillUp.car_id == car_id).first()

    session.close()

    laufleistung = buy_kmstand + gesamt_drived_kilometers

    gesamt = gesamt_insurance + gesamt_tank_cost + gesamt_tax + gesamt_repair
    gesamt_pro_kilometer = round((gesamt / gesamt_drived_kilometers) * 100,
                                 2) if gesamt_drived_kilometers > 0 else "---"
    gesamtkosten_inkl_kaufpreis = gesamt + buy_cost
    gesamt_pro_kilometer_inkl_kaufpreis = round((gesamtkosten_inkl_kaufpreis / gesamt_drived_kilometers) * 100,
                                                2) if gesamt_drived_kilometers > 0 else "---"
    if fill_up_first:
        # todo: berechnung anhand des ersten tankens, nicht unbedingt mit versicherung/steuer und wartung gleich!
        first_entry_date = fill_up_first.date  # todo: is the first entr from table, but not the first entry according to time/date!
        # stackoverflow 4040338
        amount_months = (
                                datetime.datetime.now().year - first_entry_date.year) * 12 + datetime.datetime.now().month - first_entry_date.month

        if amount_months == 0:
            amount_months = 1
            # when 0 months, it is the current month, so
        if amount_months > 0:
            costs_per_month_inkl_kaufpreis = round((gesamtkosten_inkl_kaufpreis / amount_months), 2)
            costs_per_month_ohne_kaufpreis = round((gesamt / amount_months), 2)
        else:
            costs_per_month_inkl_kaufpreis = "--- Einträge liegen in der Zukunft"
            costs_per_month_ohne_kaufpreis = "--- Einträge liegen in der Zukunft"
    else:
        costs_per_month_inkl_kaufpreis = 0
        costs_per_month_ohne_kaufpreis = 0

    list_costs_per_kilometer = []
    for year in list_table_data:
        if isinstance(year["costs_per_kilometer"], str):
            # skip entries without data, "---" is the value for these entries
            continue
        list_costs_per_kilometer.append(year["costs_per_kilometer"])
    durchschnitt_pro_kilometer = round(mean(list_costs_per_kilometer * 100), 2) if list_costs_per_kilometer else "---"

    return render_template('kostenubersicht.html', list_table_data=list_table_data, gesamt_tank_cost=gesamt_tank_cost,
                           gesamt_drived_kilometers=gesamt_drived_kilometers, gesamt_insurance=gesamt_insurance,
                           gesamt_tax=gesamt_tax, gesamt_repair=gesamt_repair, buy_cost=buy_cost,
                           buy_kmstand=buy_kmstand, gesamt=gesamt, gesamt_pro_kilometer=gesamt_pro_kilometer,
                           durchschnitt_pro_kilometer=durchschnitt_pro_kilometer, laufleistung=laufleistung,
                           gesamtkosten_inkl_kaufpreis=gesamtkosten_inkl_kaufpreis,
                           gesamt_pro_kilometer_inkl_kaufpreis=gesamt_pro_kilometer_inkl_kaufpreis,
                           costs_per_month_inkl_kaufpreis=costs_per_month_inkl_kaufpreis,
                           costs_per_month_ohne_kaufpreis=costs_per_month_ohne_kaufpreis, title="Kostenübersicht")


@app.route('/versicherung')
@flask_login.login_required
def versicherung():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    insurances = session.query(CarInsurance).filter(CarInsurance.car_id == car_id).all()
    session.close()
    return render_template('versicherung.html', insurances=insurances, title="Versicherung")


@app.route('/versicherung/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neue_versicherung():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        return render_template('add_new_versicherung.html', title="Versicherung hinzufügen")

    elif request.method == 'POST':
        if 'date' in request.form and 'cost' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            date = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            return "falsches Datum ", 400

        if "description" in request.form:
            description = request.form['description']
        else:
            description = ''
        try:
            cost = float(request.form['cost'])
        except ValueError:
            return "falscher Wert ", 400

        if cost < 0:
            return "negativer Wert nicht zulässig", 400

        if cost == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        car_insurance = CarInsurance(car_id=car_id, date=date, cost=cost, description=description)
        session.add(car_insurance)
        session.commit()
        session.close()

        return redirect(url_for('versicherung'))


@app.route('/auto/neu', methods=['GET', 'POST'])
@flask_login.login_required
def new_car():
    if request.method == 'GET':
        return render_template('new_auto.html', title="Auto hinzufügen")
    elif request.method == 'POST':
        if 'make' not in request.form or 'model' not in request.form or 'year' not in request.form or 'buy_cost' not in request.form or 'buy_kmstand' not in request.form or 'consumption_green' not in request.form or 'consumption_red' not in request.form:
            return "fehlender Wert ", 400

        try:
            buy_cost = float(request.form['buy_cost'])
            buy_kmstand = float(request.form['buy_kmstand'])
            consumption_green = float(request.form['consumption_green'])
            consumption_red = float(request.form['consumption_red'])
        except ValueError:
            return "falscher Wert ", 400

        if buy_cost < 0 or buy_kmstand < 0:
            return "negativer Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        # create car
        car_new = Car(make=request.form['make'], model=request.form['model'], year=request.form['year'],
                      buy_cost=buy_cost, buy_kmstand=buy_kmstand, consumption_green=consumption_green,
                      consumption_red=consumption_red)

        # car user zuweisen
        user_car = UserCar(name=flask_login.current_user.id, car=car_new)
        session.add(user_car)
        session.commit()

        resp = make_response(redirect(url_for('select_car')))
        resp.set_cookie(key='car_id', value=str(car_new.car_id),
                        expires=datetime.datetime.now() + datetime.timedelta(weeks=4), httponly=True, samesite='Strict')
        session.close()

        return resp


@app.route('/auswahl_auto', methods=['GET', 'POST'])
@flask_login.login_required
def select_car():
    if request.method == 'GET':
        Session = sessionmaker(bind=engine)
        session = Session()

        if session.query(Car).join(UserCar).filter_by(name=flask_login.current_user.id).count() == 0:
            # when no car exists (yet)
            session.close()
            return redirect(url_for('new_car') + "#car_missing")

        # existing_cars = session.query(Car).all()
        # existing_user_cars = session.query(UserCar).filter_by(name=flask_login.current_user.id).all()
        existing_user_cars = session.query(Car).join(UserCar).filter_by(name=flask_login.current_user.id).all()
        session.close()

        valid_car_selected = False
        car_id = request.cookies.get('car_id')
        if valid_car(car_id):
            car_id = int(car_id)
            valid_car_selected = True

        selected_car = False
        for existing_car in existing_user_cars:
            if valid_car_selected and existing_car.car_id == car_id:
                existing_car.selected = True
                selected_car = True
            else:
                existing_car.selected = False

        return render_template('selection_auto.html', title="Auto auswählen", existing_cars=existing_user_cars,
                               selected_car=selected_car)
    elif request.method == 'POST':
        resp = make_response(jsonify({"status": "0"}))
        if 'selected_car_id' in request.form:
            car_id = request.form['selected_car_id']
            if valid_car(car_id):
                Session = sessionmaker(bind=engine)
                session = Session()
                car = session.query(Car).filter(Car.car_id == car_id).scalar()
                if car:
                    resp = make_response(jsonify({"status": "1"}))
                    resp.set_cookie(key='car_id', value=str(car_id),
                                    expires=datetime.datetime.now() + datetime.timedelta(weeks=4), httponly=True,
                                    samesite='Strict')
                session.close()
        return resp


@app.route('/auto', methods=['GET', 'POST'])
@flask_login.login_required
def change_car():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        Session = sessionmaker(bind=engine)
        session = Session()

        car = session.query(Car).filter(Car.car_id == car_id).first()
        if not car:
            session.close()
            return redirect(url_for('select_car'))
        session.close()

        return render_template('change_auto.html', car=car, title="Auto ändern")

    elif request.method == 'POST':
        resp = make_response(jsonify({"status": "0"}))

        if 'che_make' not in request.form or 'che_model' not in request.form or 'che_year' not in request.form or 'che_buy_cost' not in request.form or 'che_buy_kmstand' not in request.form or 'consumption_green' not in request.form or 'consumption_red' not in request.form:
            return "fehlender Wert ", 400

        try:
            buy_cost = float(request.form['che_buy_cost'])
            buy_kmstand = float(request.form['che_buy_kmstand'])
            consumption_green = float(request.form['consumption_green'])
            consumption_red = float(request.form['consumption_red'])
        except ValueError:
            return "falscher Wert ", 400

        if buy_cost < 0 or buy_kmstand < 0:
            return "negativer Wert nicht zulässig", 400

        if buy_cost == 0 or buy_kmstand == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        car = session.query(Car).filter(Car.car_id == car_id).first()

        car.make = request.form['che_make']
        car.model = request.form['che_model']
        car.year = request.form['che_year']
        car.consumption_green = consumption_green
        car.consumption_red = consumption_red
        car.buy_cost = buy_cost
        car.buy_kmstand = buy_kmstand
        session.commit()

        session.close()
        resp = make_response(jsonify({"status": "1"}))
        return resp


@app.route('/versicherung/<insurance_id>/', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_insurance(insurance_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        try:
            insurance_id = int(insurance_id)
        except ValueError:
            return "id muss eine zahl sein ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(CarInsurance).filter(CarInsurance.car_id == car_id).filter_by(
            car_insurance_id=insurance_id).first()
        session.close()
        return render_template('change_versicherung.html', insurance=entry, title="Versicherung Eintrag ändern")
    elif request.method == 'POST':
        if 'che_car_insurance_id' in request.form and 'che_cost' in request.form and 'che_description' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            insurance_id = int(insurance_id)
            car_insurance_id = int(request.form['che_car_insurance_id'])
            cost = float(request.form['che_cost'])
        except ValueError:
            return "falscher Wert ", 400

        if car_insurance_id != insurance_id:
            return "IDs nicht identisch ", 400

        if cost < 0:
            return "negativer Wert nicht zulässig", 400

        if cost == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(CarInsurance).filter(CarInsurance.car_id == car_id).filter_by(
            car_insurance_id=car_insurance_id).first()

        entry.cost = cost
        entry.description = request.form['che_description']
        session.commit()
        session.close()
        return redirect(f"{url_for('versicherung')}#versicherung_{car_insurance_id}")
    elif request.method == 'DELETE':
        try:
            car_insurance_id = int(insurance_id)
        except ValueError:
            return "falscher Wert ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        session.query(CarInsurance).filter(CarInsurance.car_id == car_id).filter_by(
            car_insurance_id=car_insurance_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('versicherung'))


@app.route('/wartung/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neue_wartung():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        return render_template('add_new_wartung.html', title="Wartung hinzufügen")

    elif request.method == 'POST':
        if 'date' in request.form and 'cost' in request.form and 'kmstand' in request.form and 'firma' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            date = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            return "falsches Datum ", 400

        if "description" in request.form:
            description = request.form['description']
        else:
            description = ''

        if "firma" in request.form:
            firma = request.form['firma']
        else:
            firma = ''
        try:
            cost = float(request.form['cost'])
            kmstand = float(request.form['kmstand'])
        except ValueError:
            return "falscher Wert ", 400

        if cost < 0 or kmstand < 0:
            return "negativer Wert nicht zulässig", 400

        if kmstand == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        car_repaires = CarRepair(car_id=car_id, date=date, cost=cost, description=description, kmstand=kmstand,
                                 firma=firma)
        session.add(car_repaires)
        session.commit()
        session.close()
        return redirect(url_for('wartung'))


@app.route('/wartung')
@flask_login.login_required
def wartung():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    repaires = session.query(CarRepair).filter(CarRepair.car_id == car_id).all()
    session.close()
    return render_template('wartung.html', repaires=repaires, title="Wartung")


@app.route('/wartungsintervall')
@flask_login.login_required
def wartungsintervall():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    repaires_exists = session.query(RepairExist).filter(RepairExist.car_id == car_id).all()

    for repaires_exist in repaires_exists:
        repaires_dones = session.query(RepairDone).filter(RepairDone.car_id == car_id).filter(
            RepairDone.car_repair_exist_id == repaires_exist.car_repair_exist_id).all()
        for repaires_done in repaires_dones:
            if repaires_done.end_kmstand:
                repaires_done.laufzeit = repaires_done.end_kmstand - repaires_done.begin_kmstand
            else:
                buy_kmstand = session.query(Car).filter(Car.car_id == car_id).scalar().buy_kmstand
                drived_meters = session.query(FillUp).filter(FillUp.car_id == car_id).all()
                gesamt_drived_kilometers = sum([fill_up.drived_meters for fill_up in drived_meters])
                laufleistung = buy_kmstand + gesamt_drived_kilometers

                repaires_done.laufzeit = laufleistung - repaires_done.begin_kmstand
        repaires_exist.repaires_dones = repaires_dones
    session.close()
    return render_template('wartungsintervall.html', repaires_exists=repaires_exists, title="Wartungsintervall")


class tatigkeiten_form(FlaskForm):
    name = StringField(validators=[InputRequired()])
    intervall = StringField(validators=[Optional()])


@app.route('/tatigkeiten/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neue_repaires_exists():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    form = tatigkeiten_form()

    if form.validate_on_submit():
        try:
            Session = sessionmaker(bind=engine)
            session = Session()

            name = form.name.data
            intervall = form.intervall.data

            repair_exists = RepairExist(car_id=car_id, name=name, intervall=intervall)
            session.add(repair_exists)
            session.commit()
            session.close()
            return redirect(url_for('wartungsintervall'))
        except Exception as e:
            # flash(e, "danger") # dont expose error messages
            flash("Fehler!", "danger")

    return render_template("new_tatigkeiten.html",
                           form=form,
                           text="Anlegen",
                           title="Neue Kategorie erstellen",
                           btn_action="Anlegen")


@app.route('/tatigkeiten/<car_repair_exist_id>', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_repaires_exists(car_repair_exist_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    if request.method == 'DELETE':
        session.query(RepairDone).filter(RepairDone.car_id == car_id).filter_by(
            car_repair_exist_id=car_repair_exist_id).delete()  # delete done tatigkeiten, wenn kategorie gelöscht wird
        session.query(RepairExist).filter(RepairExist.car_id == car_id).filter_by(
            car_repair_exist_id=car_repair_exist_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('wartungsintervall'))

    form = tatigkeiten_form()

    if form.validate_on_submit():
        try:
            entry = session.query(RepairExist).filter(RepairExist.car_id == car_id).filter_by(
                car_repair_exist_id=car_repair_exist_id).first()

            entry.name = form.name.data
            entry.intervall = form.intervall.data
            session.commit()
            session.close()

            return redirect(f"{url_for('wartungsintervall')}#arbeit_{car_repair_exist_id}")
        except Exception as e:
            # flash(e, "danger") # dont expose error messages
            flash("Fehler!", "danger")

    if request.method == 'GET':
        entry = session.query(RepairExist).filter(RepairExist.car_id == car_id).filter_by(
            car_repair_exist_id=car_repair_exist_id).first()
        form.name.data = entry.name
        form.intervall.data = entry.intervall
        session.close()

    return render_template("change_tatigkeiten.html",
                           form=form,
                           text="Ändern",
                           car_repair_exist_id=car_repair_exist_id,
                           title="Kategorie bearbeiten",
                           btn_action="Ändern")


class tatigkeiten_done_form(FlaskForm):
    car_repair_exist_id = StringField(validators=[InputRequired()])
    description = StringField(validators=[Optional()])
    begin_date = DateField(validators=[InputRequired()])
    begin_kmstand = DecimalField(validators=[InputRequired(), NumberRange(min=0.00)])
    end_kmstand = DecimalField(validators=[Optional(), NumberRange(min=0.01)])
    end_date = DateField(validators=[Optional()])


@app.route('/tatigkeiten/<car_repair_exist_id>/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neue_repaires_done(car_repair_exist_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    form = tatigkeiten_done_form()

    car_repair_exist = session.query(RepairExist).filter(RepairExist.car_repair_exist_id == car_repair_exist_id).first()
    if not car_repair_exist:
        session.close()
        flash(
            f"Arbeit nicht gefunden! <a href=\"{url_for('neue_repaires_exists')}\">Hier</a> zuerst einen neuen Eintrag erstellen",
            "danger")  # xss in var, as marked as safe!

    if form.validate_on_submit():
        try:
            if form.car_repair_exist_id.data != car_repair_exist_id:
                session.close()
                flash("IDs verschieden!", "danger")

            description = form.description.data
            begin_date = form.begin_date.data
            end_date = form.end_date.data
            begin_kmstand = round(form.begin_kmstand.data, 2)
            if form.end_kmstand.data:
                end_kmstand = round(form.end_kmstand.data, 2)
            else:
                end_kmstand = form.end_kmstand.data

            repair_done = RepairDone(car_id=car_id, repair_exists=car_repair_exist, description=description,
                                     begin_date=begin_date, begin_kmstand=begin_kmstand, end_kmstand=end_kmstand,
                                     end_date=end_date)

            print(repair_done)
            session.add(repair_done)
            session.commit()
            session.close()
            return redirect(url_for('wartungsintervall'))
        except Exception as e:
            # flash(e, "danger") # dont expose error messages # xss in var, as marked as safe!
            flash("Fehler!", "danger")

    if request.method == 'GET':
        last_entry = session.query(RepairDone).filter(RepairDone.car_id == car_id).filter_by(
            car_repair_exist_id=car_repair_exist_id).order_by(RepairDone.car_repair_done_id.desc()).first()
        if last_entry:
            # only if entry was present
            form.begin_kmstand.data = last_entry.end_kmstand
            form.begin_date.data = last_entry.end_date
        session.close()
    form.car_repair_exist_id.data = car_repair_exist_id
    return render_template("new_tatigkeiten_done.html",
                           form=form,
                           car_repair_exist=car_repair_exist,
                           text="Anlegen",
                           title="Neue Eintrag erstellen",
                           btn_action="Anlegen")


@app.route('/done_tatigkeiten/<car_repair_done_id>', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_repaires_done(car_repair_done_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    try:
        car_repair_done_id = int(car_repair_done_id)
    except ValueError:
        return "falscher Wert ", 400

    Session = sessionmaker(bind=engine)
    session = Session()
    session2 = Session()

    if request.method == 'DELETE':
        session.query(RepairDone).filter(RepairDone.car_id == car_id).filter_by(
            car_repair_done_id=car_repair_done_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('wartung'))

    form = tatigkeiten_done_form()

    entry = session.query(RepairDone).filter(RepairDone.car_id == car_id).filter_by(
        car_repair_done_id=car_repair_done_id).first()
    car_repair_exist = session2.query(RepairExist).filter(RepairExist.car_id == car_id).filter(
        RepairExist.car_repair_exist_id == entry.car_repair_exist_id).first()

    if form.validate_on_submit():
        try:
            begin_kmstand = round(form.begin_kmstand.data, 2)
            if form.end_kmstand.data:
                end_kmstand = round(form.end_kmstand.data, 2)
            else:
                end_kmstand = form.end_kmstand.data

            entry.description = form.description.data
            entry.begin_date = form.begin_date.data
            entry.begin_kmstand = begin_kmstand
            entry.end_date = form.end_date.data
            entry.end_kmstand = end_kmstand
            session.commit()
            session.close()

            return redirect(f"{url_for('wartungsintervall')}#done_arbeit_{car_repair_done_id}")
        except Exception as e:
            # flash(e, "danger") # dont expose error messages # xss in var, as marked as safe!
            flash("Fehler!", "danger")

    if request.method == 'GET':
        form.car_repair_exist_id.data = entry.car_repair_exist_id
        form.description.data = entry.description
        form.begin_date.data = entry.begin_date
        form.begin_kmstand.data = entry.begin_kmstand
        form.end_kmstand.data = entry.end_kmstand
        form.end_date.data = entry.end_date
        session.close()

    return render_template("new_tatigkeiten_done.html",
                           form=form,
                           car_repair_exist=car_repair_exist,
                           text="Ändern",
                           title="Eintrag ändern",
                           btn_action="Ändern")


@app.route('/wartung/<repair_id>', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_repair(repair_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        try:
            repair_id = int(repair_id)
        except ValueError:
            return "id muss eine zahl sein ", 400

        Session = sessionmaker(bind=engine)
        session = Session()
        entry = session.query(CarRepair).filter(CarRepair.car_id == car_id).filter_by(
            car_repair_id=repair_id).first()
        session.close()
        return render_template('change_wartung.html', repair=entry, title="Wartung Eintrag ändern")
    elif request.method == 'POST':
        if 'che_car_repair_id' in request.form and 'che_cost' in request.form and 'che_description' in request.form and 'che_firma' in request.form and 'che_kmstand' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            repair_id = int(repair_id)
            car_repair_id = int(request.form['che_car_repair_id'])
            cost = float(request.form['che_cost'])
            kmstand = float(request.form['che_kmstand'])
        except ValueError:
            return "falscher Wert ", 400

        if car_repair_id != repair_id:
            return "IDs nicht identisch ", 400

        if cost < 0 or kmstand < 0:
            return "negativer Wert nicht zulässig", 400

        if kmstand == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(CarRepair).filter(CarRepair.car_id == car_id).filter_by(
            car_repair_id=car_repair_id).first()

        entry.cost = cost
        entry.kmstand = kmstand
        entry.description = request.form['che_description']
        entry.firma = request.form['che_firma']
        session.commit()
        session.close()
        return redirect(f"{url_for('wartung')}#wartung_{car_repair_id}")
    elif request.method == 'DELETE':
        try:
            car_repair_id = int(repair_id)
        except ValueError:
            return "falscher Wert ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        session.query(CarRepair).filter(CarRepair.car_id == car_id).filter_by(
            car_repair_id=car_repair_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('wartung'))


@app.route('/steuer/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neue_steuer():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        return render_template('add_new_steuer.html', title="Steuer hinzufügen")

    elif request.method == 'POST':
        if 'date' in request.form and 'cost' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            date = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            return "falsches Datum ", 400

        if "description" in request.form:
            description = request.form['description']
        else:
            description = ''
            # print(request.form)
        try:
            cost = float(request.form['cost'])
        except ValueError:
            return "falscher Wert ", 400

        if cost < 0:
            return "negativer Wert nicht zulässig", 400

        if cost == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        car_taxes = CarTax(car_id=car_id, date=date, cost=cost, description=description)
        session.add(car_taxes)
        session.commit()
        session.close()
        return redirect(url_for('steuer'))


@app.route('/steuer')
@flask_login.login_required
def steuer():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    Session = sessionmaker(bind=engine)
    session = Session()

    taxes = session.query(CarTax).filter(CarTax.car_id == car_id).all()
    session.close()
    return render_template('steuer.html', taxes=taxes, title="Steuer")


@app.route('/steuer/<tax_id>', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_tax(tax_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        try:
            tax_id = int(tax_id)
        except ValueError:
            return "id muss eine zahl sein ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(CarTax).filter(CarTax.car_id == car_id).filter_by(
            car_tax_id=tax_id).first()
        session.close()
        return render_template('change_steuer.html', tax=entry, title="Steuer Eintrag ändern")

    elif request.method == 'POST':
        if 'che_car_tax_id' in request.form and 'che_cost' in request.form and 'che_description' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            tax_id = int(tax_id)
            car_tax_id = int(request.form['che_car_tax_id'])
            cost = float(request.form['che_cost'])
        except ValueError:
            return "falscher Wert ", 400

        if car_tax_id != tax_id:
            return "IDs nicht identisch ", 400

        if cost < 0:
            return "negativer Wert nicht zulässig", 400

        if cost == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(CarTax).filter(CarTax.car_id == car_id).filter_by(
            car_tax_id=car_tax_id).first()

        entry.cost = cost
        entry.description = request.form['che_description']
        session.commit()
        session.close()

        return redirect(f"{url_for('steuer')}#steuer_{car_tax_id}")
    elif request.method == 'DELETE':
        try:
            car_tax_id = int(tax_id)
        except ValueError:
            return "falscher Wert ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        session.query(CarTax).filter(CarTax.car_id == car_id).filter_by(
            car_tax_id=car_tax_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('steuer'))


@app.route('/tanken/neu', methods=['GET', 'POST'])
@flask_login.login_required
def neuer_fillup():
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        return render_template('add_new_fill_up.html', title="Tanken hinzufügen")
    elif request.method == 'POST':
        if 'date' in request.form and 'gallons' in request.form and 'total_cost' in request.form and 'drived_meters' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            date = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            return "falsches Datum ", 400

        try:
            gallons = float(request.form['gallons'])
            total_cost = float(request.form['total_cost'])
            drived_meters = float(request.form['drived_meters'])
        except ValueError:
            return "falscher Wert ", 400

        if gallons < 0 or total_cost < 0 or drived_meters < 0:
            return "negativer Wert nicht zulässig", 400

        if gallons == 0 or total_cost == 0 or drived_meters == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        fill_up = FillUp(car_id=car_id, gallons=gallons, total_cost=total_cost, date=date,
                         drived_meters=drived_meters)
        session.add(fill_up)
        session.commit()
        session.close()

        # optional redirect
        if 'next_redirect' in request.form:
            next_redirect = redirect_to(request.form['next_redirect'])
            return redirect(next_redirect)

        return redirect(url_for('tanken'))


@app.route('/fillup/<fillup_id>', methods=['GET', 'POST', 'DELETE'])
@flask_login.login_required
def edit_fillup(fillup_id):
    car_id = request.cookies.get('car_id')
    if not valid_car(car_id):
        return redirect(url_for('select_car'))

    if request.method == 'GET':
        try:
            fillup_id = int(fillup_id)
        except ValueError:
            return "id muss eine zahl sein ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(FillUp).filter(FillUp.car_id == car_id).filter_by(
            fill_up_id=fillup_id).first()
        session.close()
        return render_template('change_fill_up.html', fill_up=entry, title="Tanken ändern")
    elif request.method == 'POST':
        if 'che_fill_up_id' in request.form and 'che_gallons' in request.form and 'che_total_cost' in request.form and 'che_drived_meters' in request.form:
            pass
        else:
            return "fehlender Wert ", 400

        try:
            fillup_id = int(fillup_id)
            fill_up_id = int(request.form['che_fill_up_id'])
            gallons = float(request.form['che_gallons'])
            total_cost = float(request.form['che_total_cost'])
            drived_meters = float(request.form['che_drived_meters'])
        except ValueError:
            return "falscher Wert ", 400

        if fill_up_id != fillup_id:
            return "IDs nicht identisch ", 400

        if gallons < 0 or total_cost < 0 or drived_meters < 0:
            return "negativer Wert nicht zulässig", 400

        if gallons == 0 or total_cost == 0 or drived_meters == 0:
            return "Null als Wert nicht zulässig", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        entry = session.query(FillUp).filter(FillUp.car_id == car_id).filter_by(
            fill_up_id=fill_up_id).first()

        entry.gallons = gallons
        entry.total_cost = total_cost
        entry.drived_meters = drived_meters
        session.commit()
        session.close()
        return redirect(f"{url_for('tanken')}#tankeintrag_{fill_up_id}")
    elif request.method == 'DELETE':
        try:
            fillup_id = int(fillup_id)
        except ValueError:
            return "falscher Wert ", 400

        Session = sessionmaker(bind=engine)
        session = Session()

        session.query(FillUp).filter(FillUp.car_id == car_id).filter_by(
            fill_up_id=fillup_id).delete()

        session.commit()
        session.close()
        return redirect(url_for('tanken'))


@app.route('/lib/5/index_js', methods=['GET'])
@flask_login.login_required
def return_files_amcharts_index_js():
    return send_file('amcharts5/index.js')


@app.route('/lib/5/xy_js', methods=['GET'])
@flask_login.login_required
def return_files_amcharts_xy_js():
    return send_file('amcharts5/xy.js')


@app.route('/lib/5/themes/Animated_js', methods=['GET'])
@flask_login.login_required
def return_files_amcharts_animated_js():
    return send_file('amcharts5/themes/Animated.js')


@app.route('/bulma/css/bulma.min.css')
def return_bulma_css():
    return send_file('httpdocs/bulma/css/bulma.min.css')


@app.route('/manifest.json')
def return_file_manifest_json():
    return send_file('manifest.json')


@app.route('/serviceworker.js')
def return_file_serviceworker_js():
    return send_file('serviceworker.js')


@app.route('/menu_datei_js', methods=['GET'])
@flask_login.login_required
def return_file_menu_js():
    return send_file('menu.js')


@app.route('/list.js/2.3.1/list.min_js', methods=['GET'])
@flask_login.login_required
def return_file_list_js():
    return send_file('list.min.js')
