import csv
import os

from flask import Flask, session, render_template
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
    db.execute("CREATE TABLE books_bookworm (book_id SERIAL PRIMARY KEY, book_isbn VARCHAR UNIQUE NOT NULL, book_title VARCHAR NOT NULL, book_author VARCHAR NOT NULL, book_year VARCHAR NOT NULL)")
    print("Created books_bookworm")
    booklist = open("books.csv")
    reader = csv.reader(booklist)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books_bookworm (book_isbn, book_title, book_author, book_year) VALUES (:isbn, :title, :author, :year)", {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added {title} to books_bookworm")
    db.commit()

if __name__ == '__main__':
    main()
