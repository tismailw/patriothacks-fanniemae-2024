from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

#initializes the flask app
app = Flask(__name__)

'''
#mongo db 
client = MongoClient('mongodb://localhost:27017/')
db = client.myprojectdb  # This is your MongoDB database

# Example route to fetch data from MongoDB
@app.route('/get_data', methods=['GET'])
def get_data():
    data = db.test.find()  # Replace 'test' with your collection name
    result = []
    for doc in data:
        result.append({"name": doc.get("name")})
    return jsonify(result)

# Example route to insert data into MongoDB
@app.route('/add_data', methods=['POST'])
def add_data():
    data = request.json  # Get JSON data from the request
    db.test.insert_one(data)  # Insert data into 'test' collection
    return jsonify({"message": "Data added successfully!"})

'''

# Home route to render the search form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle form submission
@app.route('/search', methods=['POST'])
def search():
    budget = request.form['budget']
    area = request.form['area']
    
    # Process the data (e.g., look up houses within the budget and area)
    # For now, we'll just display what the user submitted
    return f"<h1>Search Results for Budget: ${budget}, Area: {area}</h1>"




if __name__ == '__main__':
    app.run(debug=True)
