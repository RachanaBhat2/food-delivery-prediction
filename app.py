from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re
import joblib
import numpy as np

app = Flask(__name__)
app.secret_key = '1122'

# Load saved model and encoder
model = joblib.load("delivery_time_model.pkl")
lb = joblib.load("traffic_encoder.pkl")

# ---------------------------
# Database Connection
# ---------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="", 
        database="food_db",
        port=3307
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

# Login 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address", "danger")
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['u_id']
            session['username'] = user['uname']
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Register page

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['uname']
        email = request.form['email']
        password = request.form['password']
        
        # Basic validation
        if not uname.strip():
            flash("Username is required", "danger")
            return redirect(url_for('register'))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address", "danger")
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check existing email
        cursor.execute("SELECT u_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('register'))
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (uname, email, password) VALUES (%s, %s, %s)",
            (uname, email, hashed_password)
        )
        conn.commit()

        cursor.close()
        conn.close()
        
        flash("Registration successful. Please login.", "success")
        return redirect(url_for('login'))
        
    return render_template('register.html')

#Prediction page
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    
    # Check login
    if 'user_id' not in session:
        flash("Please login to access the prediction page.", "warning")
        return redirect(url_for('login'))
    
    prediction_text = None

    if request.method == 'POST':

        #take user input
        distance = float(request.form['distance'])
        t_level = request.form['t_level']
        p_time = int(request.form['p_time'])
        experience = float(request.form['experience'])
        weather = request.form['weather']
        time = request.form['time']
        vehicle = request.form['vehicle']


        #--------Traffic level encoding-----------
        t_level = lb.transform([t_level])[0]

        # ----------- Weather Encoding ------------
        Weather_Clear = 0
        Weather_Foggy = 0
        Weather_Rainy = 0
        Weather_Snowy = 0
        Weather_Windy = 0

        if weather == "Clear":
            Weather_Clear = 1
        elif weather == "Foggy":
            Weather_Foggy = 1
        elif weather == "Rainy":
            Weather_Rainy = 1
        elif weather == "Snowy":
            Weather_Snowy = 1
        else:
            Weather_Windy = 1

        #--------Time of day encoding---------
        Time_of_Day_Afternoon=0
        Time_of_Day_Evening=0
        Time_of_Day_Morning=0
        Time_of_Day_Night=0

        if time == 'Morning':
            Time_of_Day_Morning=1
        elif time == 'Afternoon':
            Time_of_Day_Afternoon=1
        elif time == 'Evening':
            Time_of_Day_Evening=1
        else:
            Time_of_Day_Night=1
            
        #---------Vehicle type encoding------
        Vehicle_Type_Bike=0
        Vehicle_Type_Car=0
        Vehicle_Type_Scooter=0

        if vehicle == 'Bike':
            Vehicle_Type_Bike=1
        elif vehicle == 'Car':
            Vehicle_Type_Car=1
        else:
            Vehicle_Type_Scooter=1
            
        # ----------- Final Feature Vector ------------
        data = [[
            distance,
            t_level,
            p_time,
            experience,
            Weather_Clear,
            Weather_Foggy,
            Weather_Rainy,
            Weather_Snowy,
            Weather_Windy,
            Time_of_Day_Afternoon,
            Time_of_Day_Evening,
            Time_of_Day_Morning,
            Time_of_Day_Night,
            Vehicle_Type_Bike,
            Vehicle_Type_Car,
            Vehicle_Type_Scooter
        ]]

        # Convert to numpy
        data = np.array(data)

        # ----------- Prediction ------------
        prediction = model.predict(data)[0]
        prediction_text = f"Estimated Delivery Time: {round(prediction, 2)} minutes"
    
    return render_template('predict.html',prediction_text=prediction_text)

if __name__ == '__main__':
    app.run(debug=True, port=4000)
