import os, json
from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from helpers import login_required

app = Flask(__name__)
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    username = request.form.get("username")
    password=request.form.get("password")
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("error.html", header="must provide username")
        elif not request.form.get("password"):
            return render_template("error.html", header="must provide password")
        rows = db.execute("SELECT * FROM users where userl='"+username+"' and pass='"+password+"'")
        result = rows.fetchone()
        if result == None :
            return render_template("error.html", header="invalid username and/or password ")
        session["user_id"] = result[0]
        session["user_name"] = result[1]
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("error.html", header="must provide username")
        userCheck = db.execute("SELECT * FROM users WHERE userl = :username",
                          {"username":request.form.get("username")}).fetchone()
        if userCheck:
            return render_template("error.html", header="username already exist")
        elif not request.form.get("password"):
            return render_template("error.html", header="must provide password")
        elif not request.form.get("confirmation"):
            return render_template("error.html", header="must confirm password")
        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", header="passwords didn't match")
        password=request.form.get("confirmation")
        db.execute("INSERT INTO users (userl, pass) VALUES (:username, :password)",
                            {"username":request.form.get("username"),
                             "password":password})
        db.commit()
        flash('Account created', 'info')
        return redirect("/login")
    else:
        return render_template("register.html")

@app.route("/search", methods=["GET"])
@login_required
def search():
    if not request.args.get("book"):
        return render_template("error.html", message="you must provide a book.")
    query = "%" + request.args.get("book") + "%"
    query = query.title()
    rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query LIMIT 15",
                        {"query": query})

    if rows.rowcount == 0:
        return render_template("error.html", message="we can't find books with that description.")
    books = rows.fetchall()
    return render_template("results.html", books=books)

@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    if request.method == "POST":
        currentUser = session["user_id"]
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        row = db.execute("SELECT isbn FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        bookId = row.fetchone() # (id,)
        bookId = bookId[0]
        row2 = db.execute("SELECT * FROM reviews WHERE userid = :user_id AND bookid = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})
        if row2.rowcount == 1:
            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn)
        rating = int(rating)
        db.execute("INSERT INTO reviews (userid, bookid, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": currentUser,
                    "book_id": bookId,
                    "comment": comment,
                    "rating": rating})
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/book/" + isbn)
    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})
        bookInfo = row.fetchall()

        """ GOODREADS reviews """
        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})
        # Convert the response to JSON
        response = query.json()
        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]
        # Append it as the second element on the list. [1]
        bookInfo.append(response)
        """ Users reviews """
         # Search book_id by ISBN
        row = db.execute("SELECT isbn FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT * FROM reviews WHERE  bookid='"+book+"'")


        reviews = results.fetchall()

        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)

@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):

    # COUNT returns rowcount
    # SUM returns sum selected cells' values
    # INNER JOIN associates books with reviews tables

    row = db.execute("SELECT title, author, year, isbn, \
                    COUNT(reviews.userid) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.idbn = reviews.bookid \
                    WHERE isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})

    # Error checking
    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book ISBN"}), 422

    # Fetch result from RowProxy
    tmp = row.fetchone()

    # Convert to dict
    result = dict(tmp.items())

    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(result)
