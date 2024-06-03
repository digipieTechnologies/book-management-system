from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,Flask,send_from_directory
from flask_login import login_required, current_user
from models import Book, Review,User
from models import db
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask import session
from flask_mail import Mail, Message

book_blueprint = Blueprint('book_blueprint', __name__)
app = Flask(__name__, static_url_path='/static')
app.config['UPLOAD_FOLDER'] = 'static'
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'kevinjagani9428@gmail.com'
app.config['MAIL_PASSWORD'] = 'vlvf izes rlln lmfm'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'
mail = Mail(app)

@book_blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@book_blueprint.route('/add_book', methods=['POST'])
@login_required
def add_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    # Retrieve form data
    title = request.form.get('title')
    author = request.form.get('author')
    published_date_str = request.form.get('published_date')
    isbn = request.form.get('isbn')
    num_pages = request.form.get('num_pages')
    genre = request.form.get('genre')
    publisher = request.form.get('publisher')
    language = request.form.get('language')
    description = request.form.get('description')
    ratings = request.form.get('ratings')
    # Check if any of the required fields are empty
    if not all([title, author, published_date_str, isbn, num_pages, genre, publisher, language, description, ratings]):
        flash('Please fill in all the required fields.', 'error')
        return redirect(url_for('index'))
    try:
        published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid published date format. Please use YYYY-MM-DD.', 'error')
        return redirect(url_for('index'))

    # Process cover image
    if 'cover_image' in request.files:
        cover_image = request.files['cover_image']
        if cover_image.filename != '':
            filename = secure_filename(cover_image.filename)
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                flash('Invalid file format for cover image. Only JPG, JPEG, PNG, and GIF are allowed.', 'error')
                return redirect(url_for('index'))
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image_url = url_for('book_blueprint.uploaded_file', filename=filename)
        else:
            cover_image_url = None
    else:
        cover_image_url = None
    # Add the book to the database
    book = Book(
        title=title, author=author, published_date=published_date,
        isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url,
        genre=genre, publisher=publisher, language=language, description=description,
        ratings=ratings, user_id=session['user_id']
    )
    db.session.add(book)
    db.session.commit()
    send_book_added_notification(current_user.email, title)
    flash('Congratulations! Your book has been successfully added and an email notification has been sent.', 'success')
    return redirect(url_for('index'))

@book_blueprint.route('/update_book', methods=['PUT'])
@login_required
def update_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = request.form  # Get form data from request body
    book_id = data.get('book_id')  # Extract book_id from form data
    if book_id is None:
        return jsonify({'error': 'Book ID not provided'}), 400
    book = db.session.query(Book).filter(Book.id == book_id).first()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to update this book'}), 403
    # Retrieve form data
    title = data.get('title')
    author = data.get('author')
    published_date_str = data.get('published_date')
    isbn = data.get('isbn')
    num_pages = data.get('num_pages')
    cover_image_url = None
    # Handle image upload if present in form data
    if 'cover_image' in request.files:
        cover_image = request.files['cover_image']
        if cover_image.filename != '':
            filename = secure_filename(cover_image.filename)
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                return jsonify({'error': 'Invalid file format'}), 400
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image_url = url_for('uploaded_file', filename=filename)

    genre = data.get('genre')
    publisher = data.get('publisher')
    language = data.get('language')
    description = data.get('description')
    ratings = data.get('ratings')

    if title:
        book.title = title
    if author:
        book.author = author
    if published_date_str:
        book.published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    if isbn:
        book.isbn = isbn
    if num_pages:
        book.num_pages = num_pages
    if cover_image_url:
        book.cover_image_url = cover_image_url
    if genre:
        book.genre = genre
    if publisher:
        book.publisher = publisher
    if language:
        book.language = language
    if description:
        book.description = description
    if ratings:
        book.ratings = ratings

    db.session.commit()
    send_book_updated_notification(current_user.email, title)
    return jsonify({
        'success': True,
        'message': 'Book updated successfully',
        'data': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'published_date': book.published_date.strftime('%Y-%m-%d') if book.published_date else None,
            'isbn': book.isbn,
            'num_pages': book.num_pages,
            'cover_image_url': book.cover_image_url,
            'genre': book.genre,
            'publisher': book.publisher,
            'language': book.language,
            'description': book.description,
            'ratings': book.ratings
        }
    }), 200


@book_blueprint.route('/delete_book/<int:book_id>', methods=['delete'])
@login_required
def delete_book(book_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    book = db.session.query(Book).filter(Book.id == book_id).first()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to delete this book'}), 403
    title = book.title
    db.session.delete(book)
    db.session.commit()
    send_book_deleted_notification(current_user.email, title)
    return jsonify({'success': True, 'message': 'Book delete successfully'}), 201
    return redirect(url_for('index'))

def send_book_added_notification(user_email, book_title):
    msg = Message('Book Added', recipients=[user_email])
    msg.body = f'Dear user, You have added a new book: {book_title}.'
    mail.send(msg)

def send_book_updated_notification(user_email, book_title):
    msg = Message('Book Updated', recipients=[user_email])
    msg.body = f'Dear user, You have updated the book: {book_title}.'
    mail.send(msg)

def send_book_deleted_notification(user_email, book_title):
    msg = Message('Book Deleted', recipients=[user_email])
    msg.body = f'Dear user, You have deleted the book: {book_title}.'
    mail.send(msg)



@book_blueprint.route('/all_books')
def all_books():
    # Fetch all books from the database
    all_books = db.session.query(Book).all()
    # Convert books to a list of dictionaries
    books_list = []
    for book in all_books:
        user_data = None
        # Check if the book has a user associated with it
        if book.user:
            # If yes, populate user data
            user_data = {
                'id': book.user.id,
                'name': book.user.name,
            }
        rating_count = len(book.reviews)
        if rating_count > 0:
            average_rating = sum(review.rating for review in book.reviews) / rating_count
        else:
            average_rating = 0
        books_list.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'published_date': str(book.published_date),  
            'genre': book.genre,
            'cover_image_url': book.cover_image_url, 
            'user': user_data,
            'rating_count': rating_count,
            'average_rating': average_rating
        })
    return jsonify({'books': books_list})

@book_blueprint.route('/books', methods=['GET'])
def render_review():
    # Fetch all books from the database
    book = Book.query.all()
    return render_template('book.html', book=book)
    
@book_blueprint.route('/create_review', methods=['GET'])
@login_required
@login_required
def render_review_form():
    book_id = request.args.get('book_id')
    if not book_id:
        return jsonify({'error': 'Book ID not provided'}), 400
    user_id = request.args.get('user_id')
    # user_id = current_user.id
    return render_template('review.html', book_id=book_id, user_id=user_id)

@book_blueprint.route('/create_review', methods=['POST'])
@login_required
def handle_review_submission():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = request.get_json()
    user_id = data.get('user_id')
    # user_id = current_user.id 
    book_id = data.get('book_id')
    rating = int(data.get('rating')) if data.get('rating') is not None else None
    comment = data.get('comment')
    timestamp_str = data.get('timestamp')
    book = Book.query.get(book_id)
    user = User.query.get(user_id)
    if not book:
        return jsonify({'error': f"Book with ID {book_id} not found"}), 404
    if not user:
        return jsonify({'error': f"User with ID {user_id} not found"}), 404

    timestamp = datetime.fromisoformat(timestamp_str)
    review = Review(
        user=user,
        user_id=user_id,
        book_id=book_id,
        book=book,
        rating=rating,
        comment=comment,
        timestamp=timestamp if timestamp else datetime.utcnow()
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({'success': 'Review created successfully'}), 200

@book_blueprint.route('/update_review', methods=['PUT'])
@login_required
def update_review():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    # data = request.get_json()  # Get JSON data from request body
    review_id = request.form.get('review_id') 
    if review_id is None:
        return jsonify({'error': 'Review ID not provided'}), 400
    review = db.session.query(Review).filter(Review.id == review_id).first()
    if review is None:
        return jsonify({'error': 'Review not found'}), 404
    if review.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to update this review'}), 403
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    if rating is not None:
        review.rating = rating
    if comment:
        review.comment = comment
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Review updated successfully',
        'data': {
            'id': review.id,
            'user_id': review.user_id,
            'book_id': review.book_id,
            'rating': review.rating,
            'comment': review.comment,
            'timestamp': review.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    }), 200

@book_blueprint.route('/delete_review', methods=['POST'])
@login_required
def delete_review():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = request.get_json()
    review_id = data.get('review_id')
    if review_id is None:
        return jsonify({'error': 'Invalid review ID provided'}), 400
    review = db.session.query(Review).get(review_id)
    if not review:
        return jsonify({'error': f"Review with ID {review_id} not found"}), 404
    db.session.delete(review)
    db.session.commit()
    return jsonify({'success': 'Review deleted successfully'}), 200

app.register_blueprint(book_blueprint)
if __name__ == '__main__':
    
    app.run(debug=True)