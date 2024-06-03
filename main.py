from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, jsonify, flash
from graphene import ObjectType, Schema, Int
from graphene_sqlalchemy import SQLAlchemyObjectType
from sqlalchemy import or_
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from flask_sqlalchemy import SQLAlchemy
from flask_graphql import GraphQLView
from flask_login import LoginManager, UserMixin, logout_user, login_user, login_required, current_user
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from flask_swagger_ui import get_swaggerui_blueprint
from flask_paginate import Pagination, get_page_args
from functools import wraps
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import graphene
from graphql import GraphQLError
from models import User,Book,Review
from routs import book_blueprint
from models import db
app = Flask(__name__, static_url_path='/static')

# Define a decorator to restrict access to admin routes
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('admin_panel'))
        return func(*args, **kwargs)
    return decorated_view

SWAGGER_URL = '/swagger'  
API_URL = '/static/swagger.json'  

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={ 
        'app_name': "Book Management System"
    },
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

app.config['JWT_SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SECRET_KEY'] = '9494'
db.init_app(app)

jwt = JWTManager(app)
login_manager = LoginManager(app)
login_manager.init_app(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'kevinjagani9428@gmail.com'
app.config['MAIL_PASSWORD'] = 'vlvf izes rlln lmfm'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'
mail = Mail(app)
app.register_blueprint(book_blueprint)

class UserType(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the user", required=True)

    def resolve_id(self, info):
        return str(self.id)

# Define GraphQL types
class BookType(SQLAlchemyObjectType):
    class Meta:
        model = Book
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the book", required=True)
    reviews = graphene.List(lambda: ReviewType)

    def resolve_id(self, info):
        return str(self.id)

    def resolve_reviews(self, info):
        return [review for review in self.reviews]

# Update resolver functions for ReviewType
class ReviewType(SQLAlchemyObjectType):
    class Meta:
        model = Review
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the review", required=True)
    user = graphene.String()  
    book = graphene.String()  

    def resolve_user(self, info):
        return f"/users/{self.user_id}"

    def resolve_book(self, info):
        return f"/books/{self.book_id}"

@login_manager.user_loader
def loader_user(user_id):
    return db.session.query(User).get(user_id)
    
with app.app_context():
    db.create_all()

# Admin panel route
@app.route('/admin/panel')

def admin_panel():
    books_with_users = db.session.query(Book, User).join(User).all()
    total_books = db.session.query(Book).count()
    total_users = db.session.query(User).count()
    return render_template('admin_panel.html', books_with_users=books_with_users, total_books=total_books, total_users=total_users)

@app.route('/login', methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash('Both email and password are required!!', 'login_error')
            return redirect(url_for('login_page'))
        user = db.session.query(User).filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            access_token=create_access_token(identity=user.id)
            login_user(user)
            return redirect(url_for("index", message="Login successful, welcome {}!".format(user.name)))
        else:
            flash('Invalid email or password', 'login_error')
            return redirect(url_for('login_page'))
    elif request.method == "GET":
        return render_template('login.html')

@app.route('/register', methods=["POST"])
def register_page():
    email = request.form.get("email")
    password = request.form.get("password")
    name = request.form.get('name')
    # Check if required fields are not None
    if not email  or not password or not name :
        flash('Please fill all required fields', 'signup_error')
        return redirect(url_for('login_page'))
    if not name.isalpha():
        flash('Name must contain only letters', 'signup_error')
        return redirect(url_for('login_page'))
    if db.session.query(User).filter_by(email=email).first():
        flash('Email already exists', 'signup_error')
        return redirect(url_for('login_page'))
    if not password:
        flash('Password is required', 'signup_error')
        return redirect(url_for('login_page'))
    user = User(email=email, password=password, name=name)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    login_user(user)  
    send_welcome_email(email)
    flash('Registration successful!', 'success')
    return redirect(url_for("index"))
    # Return to login page if registration fails
    flash('Please fill all required fields', 'signup_error')
    return redirect(url_for('login_page'))

@app.route('/search')
@login_required 
def search():
    search_query = request.args.get('q')
    
    user_id = current_user.id 
    search_results = Book.query.filter(
        (Book.user_id == user_id) &
        (or_(
            Book.title.ilike(f'%{search_query}%'),
            Book.author.ilike(f'%{search_query}%'),
            Book.genre.ilike(f'%{search_query}%'), 
            Book.ratings.ilike(f'%{search_query}%'),  
            Book.published_date.ilike(f'%{search_query}%'),  
            Book.language.ilike(f'%{search_query}%')  
        ))
    ).all()
    if not search_results:
        return jsonify({'message': 'No results found for the given query.'}), 404   
    search_results_json = [book.serialize() for book in search_results]
    return jsonify(search_results_json)

@app.route('/logout', methods=["GET", "POST"])
@login_required
def logout():
    logout_user() 
    return redirect(url_for('login_page'))

@app.route('/protected', methods=['GET', 'POST'])
@jwt_required()
def protected():
    # Access protected resources
    current_user_id = get_jwt_identity()
    return {'messege':"hello user {current_user_id}"}, 200

@app.route('/')
def index():
    if 'user_id' in session: 
        user_id = session['user_id']
        message = request.args.get('message')
        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
        books = db.session.query(Book).filter(Book.user_id == user_id).offset(offset).limit(per_page).all()
        pagination = Pagination(page=page, total=len(books), record_name='books', per_page=per_page, css_framework='bootstrap4')
           # return {'message': 'The application is running'}
        return render_template('index.html', books=books, book=None, message=message, pagination=pagination)
    else:
        return redirect(url_for('login_page')) 
        
def send_welcome_email(user_email):
    msg = Message('Welcome to Book Management System', recipients=[user_email])
    msg.body = 'Dear user, Welcome to Book Management System! Thank you for registering.'
    mail.send(msg)


@app.route('/get_reviews')
def get_reviews():
    reviews = Review.query.all()
    review_data = []
    for review in reviews:
        review_data.append({
            'id': review.id,
            'user_id': review.user_id,
            'user_name': review.user.name,
            'book_id': review.book_id,
            'book_title': review.book.title, 
            'rating': review.rating,
            'comment': review.comment,
            'timestamp': review.timestamp.strftime('%Y-%m-%d %H:%M:%S')  # Convert timestamp to string format
        })
    return jsonify({'reviews': review_data})

class Query(ObjectType):
    reviews = graphene.List(ReviewType)
    users = graphene.List(UserType)
    books = graphene.List(BookType)
    book = graphene.Field(BookType, id=graphene.ID())
    def resolve_reviews(self, info):
        return db.session.query(Review).all()
    def resolve_users(self, info):
        return db.session.query(User).all()
    def resolve_books(self, info):
        return db.session.query(Book).all()
    def resolve_book(self, info, id):
        return db.session.query(Book).get(id)

class CreateReview(graphene.Mutation):
        class Arguments:
            user_id = graphene.Int(required=True)
            book_id = graphene.Int(required=True)
            rating = graphene.Int(required=True)
            comment = graphene.String()
            timestamp = graphene.DateTime()
        review = graphene.Field(ReviewType)
        def mutate(self, info, user_id, book_id, rating, comment=None, timestamp=None):
            if not 1 <= rating <= 5:
                raise GraphQLError("Rating must be between 1 and 5")
            user = db.session.query(User).get(user_id)
            book = db.session.query(Book).get(book_id)
            if not user:
                raise GraphQLError(f"User with ID {user_id} not found")
            if not book:
                raise GraphQLError(f"Book with ID {book_id} not found")
            review = Review(
                user=user,
                book=book,
                rating=rating,
                comment=comment,
                timestamp=timestamp if timestamp else datetime.utcnow()
            )
            db.session.add(review)
            db.session.commit()
            return CreateReview(review=review)

class DeleteReview(graphene.Mutation):
        class Arguments:
            reviewId = graphene.Int(required=True)
        success = graphene.Boolean()
        def mutate(self, info, reviewId):
            review = db.session.query(Review).get(reviewId)
            if not review:
                raise GraphQLError(f"Review with ID {reviewId} not found")
            db.session.delete(review)
            db.session.commit()
            return DeleteReview(success=True)

class CreateBook(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        author = graphene.String()
        published_date = graphene.Date()
        isbn = graphene.String()
        num_pages = graphene.Int()
        cover_image_url = graphene.String()
        genre = graphene.String()
        publisher = graphene.String()
        language = graphene.String()
        description = graphene.String()
        ratings = graphene.Float()
    book = graphene.Field(BookType)
    def mutate(self, info,  title, author, published_date, isbn, num_pages, cover_image_url, genre, publisher, language, description, ratings):
        db = ()
        book = Book(title=title, author=author, published_date=published_date,
                isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url,genre=genre,publisher=publisher,language=language,description=description,ratings=ratings)
        db.add(book)
        db.commit()
        db.refresh(book)
        return CreateBook(book=book)

class UpdateBook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String(required=True)
        author = graphene.String()
        published_date = graphene.Date()
        isbn = graphene.String()
        num_pages = graphene.Int()
        cover_image_url = graphene.String()
        genre = graphene.String()
        publisher = graphene.String()
        language = graphene.String()
        description = graphene.String()
        ratings = graphene.Float()
    book = graphene.Field(BookType)
    def mutate(self, info, id, title, author, published_date, isbn, num_pages, cover_image_url, genre, publisher, language, description, ratings):
        db = ()
        book=db.query(Book).filter(Book.id == id).first()
        if not book:
            raise Exception(f"Book with id {id} not found")
        book.title = title
        book.author = author
        book.published_date = published_date
        book.isbn = isbn
        book.num_pages = num_pages
        book.cover_image_url = cover_image_url
        book.genre = genre
        book.publisher = publisher
        book.language = language
        book.description = description
        book.ratings = ratings

        db.commit()
        db.refresh(book)
        return UpdateBook(book=book)

class DeleteBook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    book = graphene.Field(BookType)
    def mutate(self,info,id):
        db = ()
        book=db.query(Book).filter(Book.id == id).first()
        if not book:
             raise Exception(f"Book with id {id} not found")
        db.delete(book)
        db.commit()
        return DeleteBook(book=book)
# Define GraphQL mutations
class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()
    update_book = UpdateBook.Field()
    delete_book = DeleteBook.Field()
    create_review = CreateReview.Field()
    delete_review = DeleteReview.Field()
# Create GraphQL schema
schema = Schema(query=Query,mutation=Mutation)
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)

