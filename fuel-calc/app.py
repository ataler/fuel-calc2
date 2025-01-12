from flask import Flask, request, render_template, redirect, url_for
from sqlalchemy import create_engine, Column, Integer, Float, String, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fuel.db")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Calculation(Base):
    __tablename__ = 'calculations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    distance = Column(Float)
    fuel_per_100km = Column(Float)
    fuel_price = Column(Float, nullable=True)
    fuel_consumed = Column(Float)
    cost = Column(Float, nullable=True)

Base.metadata.create_all(engine)

def is_valid_number(value, allow_empty=False):
    if allow_empty and not value.strip():
        return True
    try:
        float(value.replace(',', '.'))
        return True
    except ValueError:
        return False

@app.route('/')
def home():
    last_five = session.query(Calculation).order_by(Calculation.id.desc()).limit(5).all()
    avg_distance = session.query(func.avg(Calculation.distance)).scalar()
    avg_fuel = session.query(func.avg(Calculation.fuel_per_100km)).scalar()
    avg_cost = session.query(func.avg(Calculation.cost)).scalar()

  
    distance = request.args.get('distance', '')
    fuel_per_100km = request.args.get('fuel_per_100km', '')
    fuel_price = request.args.get('fuel_price', '')

    result = request.args.get('result', '')
    cost = request.args.get('cost', '')

    return render_template('index.html',
                           last_five=last_five, 
                           avg_distance=avg_distance, 
                           avg_fuel=avg_fuel, 
                           avg_cost=avg_cost,
                           distance=distance, 
                           fuel_per_100km=fuel_per_100km,
                           fuel_price=fuel_price,
                           result=result,
                           cost=cost)

@app.route('/oblicz', methods=['POST'])
def calculate():
    distance = request.form['distance']
    fuel_per_100km = request.form['fuel_per_100km']
    fuel_price = request.form['fuel_price']

    errors = []

 
    if not is_valid_number(distance) or float(distance.replace(',', '.')) <= 0:
        errors.append("Dystans musi być dodatnią liczbą.")
    if not is_valid_number(fuel_per_100km) or float(fuel_per_100km.replace(',', '.')) <= 0:
        errors.append("Spalanie musi być dodatnią liczbą.")
    if fuel_price.strip() and (not is_valid_number(fuel_price) or float(fuel_price.replace(',', '.')) <= 0):
        errors.append("Cena paliwa musi być dodatnią liczbą lub pozostawiona pusta.")

  
    if errors:
        return render_template('index.html', errors=errors)


    distance_float = float(distance.replace(',', '.'))
    fuel_per_100km_float = float(fuel_per_100km.replace(',', '.'))
    fuel_consumed = (distance_float * fuel_per_100km_float) / 100


    cost = None
    if fuel_price.strip():  
        fuel_price_float = float(fuel_price.replace(',', '.'))
        cost = fuel_consumed * fuel_price_float 


    if cost is not None and cost <= 0:
        cost = None  


    new_calc = Calculation(
        distance=distance_float,
        fuel_per_100km=fuel_per_100km_float,
        fuel_price=fuel_price_float if fuel_price.strip() else None,
        fuel_consumed=fuel_consumed,
        cost=cost
    )
    session.add(new_calc)
    session.commit()


    return redirect(url_for(
        'home',
        result=round(fuel_consumed, 2),
        cost=round(cost, 2) if cost is not None else None,
        distance=distance,
        fuel_per_100km=fuel_per_100km,
        fuel_price=fuel_price
    ))



@app.route('/history')
def history():
    all_calculations = session.query(Calculation).order_by(Calculation.id.desc()).all()


    avg_distance = session.query(func.avg(Calculation.distance)).scalar()
    avg_fuel = session.query(func.avg(Calculation.fuel_per_100km)).scalar()
    avg_cost = session.query(func.avg(Calculation.cost)).scalar()


    total_distance = session.query(func.sum(Calculation.distance)).scalar() or 0
    total_fuel_consumed = session.query(func.sum(Calculation.fuel_consumed)).scalar() or 0
    total_cost = session.query(func.sum(Calculation.cost)).scalar() or 0

    avg_cost = round(avg_cost, 2) if avg_cost is not None else None
    avg_distance = round(avg_distance, 2) if avg_distance is not None else None
    avg_fuel = round(avg_fuel, 2) if avg_fuel is not None else None

    return render_template('history.html', 
                           calculations=all_calculations, 
                           avg_distance=avg_distance,
                           avg_fuel=avg_fuel, 
                           avg_cost=avg_cost,
                           total_distance=total_distance,
                           total_fuel_consumed=total_fuel_consumed,
                           total_cost=round(total_cost, 2))



@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    calc = session.query(Calculation).get(id)
    if calc:
        session.delete(calc)
        session.commit()
    return redirect('/history')

@app.route('/delete_all', methods=['GET'])
def delete_all():

    session.execute(text('DELETE FROM calculations'))
    session.commit()


    session.execute(text('ALTER SEQUENCE calculations_id_seq RESTART WITH 1'))
    session.commit()

    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
