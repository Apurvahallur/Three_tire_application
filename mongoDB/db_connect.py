from flask import Flask, render_template, request, redirect, url_for, session, send_file
from pymongo import MongoClient, ReturnDocument
import gridfs
import io
import os
from bson import ObjectId
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "super-secret-key"

DATABASE_FILE = "D:\\Documents\\python_project\\3tire_app\\mongoDB\\database.txt"

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db = client["HMB"]
collection = db["profile"]
fs = gridfs.GridFS(db)


# ========== AUTH ==========

def load_users():
    if not os.path.exists(DATABASE_FILE):
        return {}
    with open(DATABASE_FILE, "r") as f:
        users = {}
        for line in f:
            if ":" in line:
                username, password = line.strip().split(":")
                users[username] = password
        return users

def save_user(username, password):
    with open(DATABASE_FILE, "a") as f:
        f.write(f"{username}:{password}\n")

def get_next_id():
    counter = db.counters.find_one_and_update(
        {"_id": "profile_id"},
        {"$inc": {"sequence_value": 1}},
        return_document=ReturnDocument.AFTER, 
        upsert=True
    )
    return counter["sequence_value"]

@app.route("/")
def home():
    return redirect(url_for('login'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users:
            return "User already exists! Please go to login."
        save_user(username, password)
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users and users[username] == password:
            session["username"] = username
            return redirect(url_for("dashboard"))
        return "Invalid username or password!"
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("username"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


# ========== SEARCH ==========

@app.route("/search", methods=["GET", "POST"])
def search():
    if not session.get("username"):
        return redirect(url_for("login"))

    results = []
    # Dynamically detect columns
    sample_doc = collection.find_one()
    if sample_doc:
        columns = list(sample_doc.keys())
        columns.remove("_id") if "_id" in columns else None
        columns.remove("image_id") if "image_id" in columns else None
    else:
        columns = [] 

    if request.method == "POST":
        logic = request.form.get("logic", "and")
        filters = []

        for i in range(5):
            col = request.form.get(f"column{i}")
            op = request.form.get(f"operator{i}")
            val = request.form.get(f"value{i}")

            if col and op and val:
                try:
                    val = float(val)
                except:
                    val = val.strip()

                if op == "==":
                    filters.append({col: val})
                elif op == "!=":
                    filters.append({col: {"$ne": val}})
                elif op in [">", "<", ">=", "<="]:
                    mongo_op = {
                        ">": "$gt",
                        "<": "$lt",
                        ">=": "$gte",
                        "<=": "$lte"
                    }[op]
                    filters.append({col: {mongo_op: val}})
                elif op == "contains":
                    filters.append({col: {"$regex": val, "$options": "i"}})

        query = {}
        if filters:
            query = {"$and": filters} if logic == "and" else {"$or": filters}

        cursor = collection.find(query)
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            if "image_id" in doc:
                doc["image_id"] = str(doc["image_id"])
            results.append(doc)

    return render_template(
        "search.html",
        results=results,
        columns=columns,
        all_columns=columns,
        form_data=request.form if request.method == "POST" else {}
    )

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("username"):
        return redirect(url_for("login"))

    if request.method == "POST":
        profile_id = get_next_id()

        data = {
            "ID": profile_id,
            "Name": request.form.get("name"),
            "Age": int(request.form.get("age")),
            "Gender": request.form.get("gender"),
            "Caste": request.form.get("caste"),
            "Religion": request.form.get("religion"),
            "Education": request.form.get("education"),
            "Height": float(request.form.get("height")),
            "Salary(LPA)": float(request.form.get("salary")),
            "Phone": request.form.get("phone"),
        }

        # Handle image upload
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            image_id = fs.put(image_file, filename=image_file.filename)
            data["image_id"] = image_id

        collection.insert_one(data)
        return redirect(url_for("search"))

    return render_template("upload.html")

# ========== IMAGE FETCH ROUTE ==========

@app.route("/image/<image_id>")
def get_image(image_id):
    try:
        file = fs.get(ObjectId(image_id))
        return send_file(io.BytesIO(file.read()), mimetype="image/jpeg")
    except:
        return "Image not found", 404

@app.route("/edit/<doc_id>", methods=["GET", "POST"])
def edit(doc_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    doc = collection.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        return "Profile not found", 404

    if request.method == "POST":
        updated_data = {
            "Name": request.form.get("name"),
            "Age": int(request.form.get("age")),
            "Gender": request.form.get("gender"),
            "Phone": request.form.get("phone"),
            "Education": request.form.get("education"),
            "Religion": request.form.get("religion"),
            "Caste": request.form.get("caste"),
            "Height": float(request.form.get("height")),
            "Salary(LPA)": float(request.form.get("salary"))
        }

        # Handle new image upload
        image = request.files.get("image")
        if image:
            image_id = fs.put(image, filename=image.filename)
            updated_data["image_id"] = image_id

        collection.update_one({"_id": ObjectId(doc_id)}, {"$set": updated_data})
        return redirect(url_for("search"))

    return render_template("edit.html", doc=doc)

@app.route("/delete_image/<doc_id>")
def delete_image(doc_id):
    from bson import ObjectId

    # Find the document
    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return "Document not found", 404

    # If it has an image_id, delete image from GridFS
    image_id = doc.get("image_id")
    if image_id:
        try:
            fs.delete(image_id)
        except:
            pass  # In case file is already gone or invalid

    # Remove the image_id field from the document
    collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$unset": {"image_id": ""}}
    )

    return redirect(url_for("search"))

if __name__ == "__main__":
    app.run(debug=True)