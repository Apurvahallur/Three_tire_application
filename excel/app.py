from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
import pandas as pd
import io

app = Flask(__name__)
DATABASE_FILE = "database.txt"
EXCEL_FILE = "HMB.xlsx"
app.secret_key = "super-secret-key"

# Load user data from text file
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

# Save new user
def save_user(username, password):
    with open(DATABASE_FILE, "a") as f:
        f.write(f"{username}:{password}\n")

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
            return redirect(url_for("search"))
        return "Invalid username or password!"
    return render_template("login.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    results = None
    if not session.get("username"):
        return redirect(url_for("login"))
    
    df = pd.read_excel(EXCEL_FILE)
    columns = df.columns.tolist()

    if request.method == "POST":
        conditions = []

        for i in range(5):  # Allows up to 5 conditions
            col = request.form.get(f"column{i}")
            op = request.form.get(f"operator{i}")
            val = request.form.get(f"value{i}")

            if not col or not op or val is None or val.strip() == "":
                continue  # skip incomplete conditions

            series = df[col]

            try:
                # Try numeric comparison first
                val_numeric = float(val)
                series = pd.to_numeric(series, errors="coerce")

                if op == "==":
                    condition = series == val_numeric
                elif op == "!=":
                    condition = series != val_numeric
                elif op == ">":
                    condition = series > val_numeric
                elif op == "<":
                    condition = series < val_numeric
                elif op == ">=":
                    condition = series >= val_numeric
                elif op == "<=":
                    condition = series <= val_numeric
                else:
                    continue
            except ValueError:
                # Fall back to string comparison
                series = series.astype(str).str.lower()
                val = val.strip().lower()
                if op == "==":
                    condition = series == val
                elif op == "!=":
                    condition = series != val
                elif op == "contains":
                    condition = series.str.contains(val, na=False)
                else:
                    continue

            conditions.append(condition)

        if conditions:
            final = conditions[0]
            for cond in conditions[1:]:
                final &= cond
            df = df[final]

        results = df.to_dict(orient="records")

    return render_template("search.html", results=results, columns=columns, all_columns=columns, form_data=request.form if request.method == "POST" else {})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
