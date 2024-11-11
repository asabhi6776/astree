from flask import Flask, render_template, request, redirect, url_for, session, flash
# from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import certifi
from pymongo import MongoClient
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Configuring MongoDB with certifi
client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
mongo = client['astree-flask']

# Home page displaying public links
@app.route('/<username>')
def public_page(username):
    user = mongo.db.users.find_one({"username": username})
    if user:
        links = mongo.db.links.find({"user_id": user["_id"]})
        return render_template("public_page.html", username=username, links=links)
    return "User not found", 404

# Admin login route
@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = mongo.db.users.find_one({"username": username})

        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials")
    return render_template("admin.html")

# Admin dashboard for managing links
@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("admin"))

    if request.method == "POST":
        link_name = request.form["name"]
        link_url = request.form["url"]
        mongo.db.links.insert_one({
            "user_id": ObjectId(session["user_id"]),
            "name": link_name,
            "url": link_url,
            "clicks": 0,
            "created_at": datetime.datetime.utcnow()
        })
        return redirect(url_for("dashboard"))

    links = mongo.db.links.find({"user_id": ObjectId(session["user_id"])})
    return render_template("dashboard.html", links=links)

# Link delete route
@app.route('/delete_link/<link_id>', methods=["POST"])
def delete_link(link_id):
    if "user_id" in session:
        mongo.db.links.delete_one({"_id": ObjectId(link_id)})
        return redirect(url_for("dashboard"))
    return redirect(url_for("admin"))

# Track link clicks
@app.route('/click/<link_id>')
def click_link(link_id):
    link = mongo.db.links.find_one({"_id": ObjectId(link_id)})
    if link:
        mongo.db.links.update_one({"_id": ObjectId(link_id)}, {"$inc": {"clicks": 1}})
        return redirect(link["url"])
    return "Link not found", 404

# User logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("admin"))

# Create a new user route
@app.route('/create_user', methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = mongo.db.users.find_one({"username": username})

        if existing_user:
            flash("Username already exists")
        else:
            hashed_password = generate_password_hash(password)
            mongo.db.users.insert_one({
                "username": username,
                "password": hashed_password
            })
            flash("User created successfully")
            return redirect(url_for("admin"))

    return render_template("create_user.html")

if __name__ == "__main__":
    app.run(debug=True)
