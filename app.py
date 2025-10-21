import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# --- 基本設定 ---
app.config['SECRET_KEY'] = os.urandom(24)

# --- データベース設定 ---
# PythonAnywhereの永続ストレージに対応した設定
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- タイムゾーン設定 ---
JST = timezone(timedelta(hours=9), 'JST')

# --- ログインマネージャー設定 ---
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- データベースモデル定義 (更新) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def to_dict(self): return {'id': self.id, 'name': self.name, 'email': self.email}

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    # 概要を保存する列を追加
    description = db.Column(db.Text, nullable=True)
    is_loaned = db.Column(db.Boolean, default=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    registered_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    registered_by = db.relationship('User', foreign_keys=[registered_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'description': self.description,
            'is_loaned': self.is_loaned,
            'borrower_id': self.borrower_id,
            'registered_by_id': self.registered_by_id
        }

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=lambda: datetime.now(JST))
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    
    book = db.relationship('Book', backref=db.backref('loans', lazy=True, cascade="all, delete-orphan"))
    user = db.relationship('User', backref=db.backref('loans', lazy=True))

    def to_dict(self):
        return { 'id': self.id, 'book_id': self.book_id, 'user_id': self.user_id, 'loan_date': self.loan_date.isoformat(), 'due_date': self.due_date.isoformat(), 'return_date': self.return_date.isoformat() if self.return_date else None, 'book_title': self.book.title if self.book else "削除された書籍", 'user_name': self.user.name }

# --- APIエンドポイント ---
@app.route('/')
def index(): return render_template('index.html')

# --- 認証API (変更なし) ---
# ... (変更がないため省略) ...

# --- 図書・貸出API (更新) ---
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Book.query.order_by(Book.title).all()
    return jsonify([book.to_dict() for book in books])

# 本の詳細情報を取得するAPIを新設
@app.route('/api/books/<int:book_id>/details', methods=['GET'])
def get_book_details(book_id):
    book = Book.query.get_or_404(book_id)
    book_data = book.to_dict()
    
    if book.is_loaned:
        active_loan = Loan.query.filter_by(book_id=book.id, return_date=None).first()
        if active_loan:
            book_data['due_date'] = active_loan.due_date.isoformat()
            
    return jsonify(book_data)

@app.route('/api/books', methods=['POST'])
@login_required
def add_book():
    data = request.json
    isbn = data.get('isbn') if data.get('isbn') else None
    if isbn and Book.query.filter_by(isbn=isbn).first(): return jsonify({'error': 'このISBNは既に使用されています'}), 400
    
    new_book = Book(
        title=data['title'], 
        author=data['author'], 
        isbn=isbn, 
        description=data.get('description'), # 概要を保存
        registered_by_id=current_user.id
    )
    db.session.add(new_book)
    db.session.commit()
    return jsonify(new_book.to_dict()), 201

@app.route('/api/books/<int:book_id>', methods=['PUT'])
@login_required
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.registered_by_id != current_user.id:
        return jsonify({'error': 'この図書を編集する権限がありません'}), 403
    
    data = request.json
    book.title = data.get('title', book.title)
    book.author = data.get('author', book.author)
    book.isbn = data.get('isbn', book.isbn)
    book.description = data.get('description', book.description) # 概要を更新
    db.session.commit()
    return jsonify(book.to_dict())

@app.route('/api/books/<int:book_id>', methods=['DELETE'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.registered_by_id != current_user.id:
        return jsonify({'error': 'この図書を削除する権限がありません'}), 403
    if book.is_loaned:
        return jsonify({'error': '貸出中の図書は削除できません'}), 400
    
    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': '図書を削除しました'})

# 貸出履歴APIをログインユーザー専用に修正
@app.route('/api/loans', methods=['GET'])
@login_required
def get_loans():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.loan_date.desc()).all()
    return jsonify([loan.to_dict() for loan in loans])
    
# ... (他のAPIエンドポイントは変更なし) ...

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

