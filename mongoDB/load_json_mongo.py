import json
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["HMB"]
collection = db["profile"]

# Load JSON file
with open("D:\\Documents\\python_project\\3tire_app\\mongoDB\\HMB.json", "r") as file:
    data = json.load(file)

# Insert data
if isinstance(data, list):
    collection.insert_many(data)
else:
    collection.insert_one(data)

print("Data inserted successfully!")
