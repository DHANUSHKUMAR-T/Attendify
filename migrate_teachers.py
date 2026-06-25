"""
One-time migration script: copies teachers from teachers.json -> MongoDB
Run once locally, then it can be deleted.
"""
from pymongo import MongoClient
import json, os

MONGO_URI = "mongodb+srv://tdhanu:Dhanu123@clustersumma.ggzzczb.mongodb.net/attendance_db?retryWrites=true&w=majority&appName=ClusterSumma"
client = MongoClient(MONGO_URI)
db = client["attendance_db"]
teachers_collection = db["teachers"]

# Create unique index
teachers_collection.create_index("username", unique=True)

TEACHERS_FILE = os.path.join(os.path.dirname(__file__), "teachers.json")
if os.path.exists(TEACHERS_FILE):
    with open(TEACHERS_FILE, "r") as f:
        teachers = json.load(f)
    for username, doc in teachers.items():
        teachers_collection.update_one({"username": username}, {"$set": doc}, upsert=True)
        print(f"Migrated: {username} ({doc['name']}) - {doc['role']}")
else:
    print("No teachers.json found, skipping migration.")

print("\nDone! Teachers now in MongoDB:")
for t in teachers_collection.find({}, {"_id": 0, "password": 0}):
    print(t)
