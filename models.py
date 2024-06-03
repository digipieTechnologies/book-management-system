from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import Flask
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "user"  
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 
    reviews = relationship("Review", back_populates="user")
    books = relationship("Book", back_populates="user")

# Define SQLAlchemy models
class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, index=True)
    author = db.Column(db.String, index=True)
    published_date = db.Column(db.Date)
    isbn = db.Column(db.String, index=True)
    num_pages = db.Column(db.Integer)
    cover_image_url = db.Column(db.String, nullable=True)
    genre = db.Column(db.String) 
    publisher = db.Column(db.String)  
    language = db.Column(db.String)  
    description = db.Column(db.String)  
    ratings = db.Column(db.Float)  
    user_id = db.Column(db.Integer, ForeignKey('user.id'))  
    reviews = relationship("Review", back_populates="book")
    user = relationship("User", back_populates="books")
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'published_date': self.published_date.strftime('%Y-%m-%d'),  # Format date as string
            'isbn': self.isbn,
            'num_pages': self.num_pages,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre,  
            'publisher': self.publisher,
            'language': self.language,
            'description': self.description,
            'ratings': self.ratings
        }

# Add this to your existing SQLAlchemy models
class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rating = db.Column(db.Integer)
    comment = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship("User", back_populates="reviews")

    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    book = relationship("Book", back_populates="reviews")

