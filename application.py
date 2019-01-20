import os
import requests
import json

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE users_bookworm (user_id SERIAL PRIMARY KEY, user_name VARCHAR UNIQUE, user_password VARCHAR NOT NULL)")
    print("Created users_bookworm table")
    db.execute("CREATE TABLE reviews_bookworm (review_id SERIAL PRIMARY KEY, review_user_name VARCHAR REFERENCES users_bookworm(user_name), review_book_isbn VARCHAR REFERENCES books_bookworm(book_isbn), review_rating INTEGER, review_comment VARCHAR)")
    print("Created reviews_bookworm table")
    db.commit()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/search_register", methods=["POST","GET"])
def search_register():
    user_name=request.form.get("user_name")
    user_password=request.form.get("user_password")
    if db.execute ("SELECT * FROM users_bookworm WHERE user_name = :user_name",{"user_name":user_name}).rowcount!=0:
        return render_template ("register.html", message="Username already exists. Try again")
    db.execute("INSERT INTO users_bookworm (user_name, user_password) VALUES (:user_name, :user_password)", {"user_name": user_name, "user_password": user_password})
    db.commit()
    return render_template("search.html", user_name=user_name, user_password=user_password, message="You have registered successfully at Bookworms")

@app.route("/search_login", methods=["POST","GET"])
def search_login():
    user_name=request.form.get("user_name")
    user_password=request.form.get("user_password")
    if db.execute ("SELECT * FROM users_bookworm WHERE user_name = :user_name AND user_password = :user_password",{"user_name":user_name, "user_password":user_password}).rowcount==0:
        return render_template ("index.html", message="Username or password is incorrect. Try again")
    db.commit()
    return render_template("search.html", user_name=user_name, user_password=user_password, message="You have logged successfully in.")

@app.route("/search_results", methods=["POST"])
def search_results():
    result_type=request.form.get("result_type")
    user_search=request.form.get("user_search")

    results1 = db.execute ("SELECT * FROM books_bookworm WHERE book_title LIKE '%"+user_search+"%'")
    results2 = db.execute ("SELECT * FROM books_bookworm WHERE book_author LIKE '%"+user_search+"%'")
    results3 = db.execute ("SELECT * FROM books_bookworm WHERE book_isbn LIKE '%"+user_search+"%'")

    if result_type=="1" and results1.rowcount==0:
        return render_template ("search.html", message="We couldn't find the title you are searching for. Try again")
    elif result_type=="2" and results2.rowcount==0:
        return render_template ("search.html", message="We couldn't find the author you are searching for. Try again")
    elif result_type=="3" and results3.rowcount==0:
        return render_template ("search.html", message="We couldn't find the ISBN you are searching for. Try again")
    else:
        return render_template ("search_results.html", results1=results1, results2=results2, results3=results3, result_type=result_type)
    db.commit()
    return render_template("search_results.html")

@app.route("/book_page/<int:id>", methods=["GET","POST"] )
def details(id):
    book_id=id
    book_title_dets = db.execute ("SELECT book_title FROM books_bookworm WHERE book_id = :id", {"id":id}).fetchone()
    book_author_dets = db.execute ("SELECT book_author FROM books_bookworm WHERE book_id = :id", {"id":id}).fetchone()
    book_year_dets = db.execute ("SELECT book_year FROM books_bookworm WHERE book_id = :id", {"id":id}).fetchone()
    book_isbn_dets = db.execute ("SELECT book_isbn FROM books_bookworm WHERE book_id = :id", {"id":id}).fetchone()

    book_isbn = db.execute ("SELECT book_isbn FROM books_bookworm WHERE book_id = :id", {"id":id})
    res=requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SdkRCgHDecZxIUwv3xWfA", "isbns": book_isbn}).json()['books'][0]
    work_ratings_count=res['work_ratings_count']
    average_rating=res['average_rating']

    db.commit()
    return render_template("book_page.html", res=res,average_rating=average_rating, work_ratings_count=work_ratings_count, book_title_dets=book_title_dets, book_author_dets=book_author_dets, book_year_dets=book_year_dets, book_isbn_dets=book_isbn_dets)

@app.route("/reviews/<string:isbn>", methods=["GET","POST"] )
def reviews(isbn):
    user_password=request.form.get("user_password")
    review_rating=request.form.get("review_rating")
    review_comment=request.form.get("review_comment")
    review_user_name=request.form.get("user_name")
    review_book_isbn=isbn
    check=db.execute ("SELECT review_user_name, review_book_isbn FROM reviews_bookworm WHERE review_user_name = :review_user_name AND review_book_isbn = :review_book_isbn",{"review_user_name":review_user_name, "review_book_isbn":review_book_isbn})
    authentication=db.execute ("SELECT * FROM users_bookworm WHERE user_name = :review_user_name AND user_password = :user_password",{"review_user_name":review_user_name, "user_password":user_password})
    other_reviews=db.execute("SELECT review_user_name, review_rating, review_comment FROM reviews_bookworm WHERE review_book_isbn=:review_book_isbn",{"review_book_isbn": review_book_isbn}).fetchall()
    each_review=db.execute("SELECT review_user_name, review_rating, review_comment FROM reviews_bookworm WHERE review_book_isbn=:review_book_isbn",{"review_book_isbn": review_book_isbn}).fetchone()

    if authentication.rowcount!=0:
        if check.rowcount!=0:
            message="You have already reviewed this book. You cannot submit more than one review for the same book."
            return render_template("review.html", review_rating=review_rating, review_comment=review_comment, check=check, other_reviews=other_reviews, each_review=each_review, message=message)
        else:
            db.execute("INSERT INTO reviews_bookworm (review_rating, review_comment, review_book_isbn, review_user_name) VALUES (:review_rating, :review_comment, :review_book_isbn, :review_user_name)", {"review_rating": review_rating, "review_comment": review_comment, "review_book_isbn": review_book_isbn, "review_user_name": review_user_name})
    else:
        message="Your username or password is incorrect. Try again to review"
        return render_template("layout.html",message=message, topic="Oops!")

    db.commit()
    return render_template("review.html", review_rating=review_rating, review_comment=review_comment, check=check, other_reviews=other_reviews, each_review=each_review)

@app.route("/api/<isbn>", methods=["GET"])
def api(isbn):
    book_isbn=isbn
    book=db.execute("SELECT * FROM books_bookworm WHERE book_isbn = :book_isbn",{"book_isbn":book_isbn}).fetchone()
    if book is None:
        return render_template("layout.html",topic="404 Error", message="The page you are looking for is not available")
    res=requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SdkRCgHDecZxIUwv3xWfA", "isbns": book_isbn}).json()
    average_rating=res['books'][0]['average_rating']
    work_ratings_count=res['books'][0]['work_ratings_count']
    message = {
        "title": book.book_title,
        "author": book.book_author,
        "year": book.book_year,
        "isbn": isbn,
        "review_count": work_ratings_count,
        "average_score": average_rating
    }
    return render_template("layout.html", res=res, message=message, topic="API Access")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return render_template("index.html")

if __name__ == '__main__':
    main()
