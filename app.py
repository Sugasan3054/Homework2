import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- データベース設定 ---
# データベースファイルのパスを設定
db_path = os.path.join(os.path.dirname(__file__), 'library.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- データベースモデル定義 ---

# 図書モデル (Book)
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    is_loaned = db.Column(db.Boolean, default=False) # 貸出中フラグ

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'is_loaned': self.is_loaned
        }

# 利用者モデル (User)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email}

# 貸出記録モデル (Loan)
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    
    # リレーションシップ
    book = db.relationship('Book', backref=db.backref('loans', lazy=True))
    user = db.relationship('User', backref=db.backref('loans', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'user_id': self.user_id,
            'loan_date': self.loan_date.isoformat(),
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'book_title': self.book.title,
            'user_name': self.user.name
        }

# --- APIエンドポイント ---

@app.route('/')
def index():
    """メインページを表示"""
    return render_template('index.html')

@app.route('/api/books', methods=['GET'])
def get_books():
    """全図書情報を取得"""
    books = Book.query.all()
    return jsonify([book.to_dict() for book in books])

@app.route('/api/books', methods=['POST'])
def add_book():
    """新しい図書を登録"""
    data = request.json
    new_book = Book(title=data['title'], author=data['author'], isbn=data.get('isbn'))
    db.session.add(new_book)
    db.session.commit()
    return jsonify(new_book.to_dict()), 201

@app.route('/api/users', methods=['GET'])
def get_users():
    """全利用者情報を取得"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/users', methods=['POST'])
def add_user():
    """新しい利用者を登録"""
    data = request.json
    new_user = User(name=data['name'], email=data.get('email'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify(new_user.to_dict()), 201

@app.route('/api/loan', methods=['POST'])
def loan_book():
    """図書を貸出"""
    data = request.json
    book_id = data['book_id']
    user_id = data['user_id']

    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    if book.is_loaned:
        return jsonify({'error': 'Book is already on loan'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # 貸出処理
    book.is_loaned = True
    new_loan = Loan(book_id=book.id, user_id=user.id)
    db.session.add(new_loan)
    db.session.commit()

    return jsonify(new_loan.to_dict()), 201

@app.route('/api/return/<int:book_id>', methods=['POST'])
def return_book(book_id):
    """図書を返却"""
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    if not book.is_loaned:
        return jsonify({'error': 'Book is not on loan'}), 400

    # 返却処理
    loan = Loan.query.filter_by(book_id=book.id, return_date=None).first()
    if not loan:
        return jsonify({'error': 'Active loan record not found'}), 404
        
    book.is_loaned = False
    loan.return_date = datetime.utcnow()
    db.session.commit()

    return jsonify(loan.to_dict())

@app.route('/api/loans', methods=['GET'])
def get_loans():
    """貸出記録を取得"""
    loans = Loan.query.order_by(Loan.loan_date.desc()).all()
    return jsonify([loan.to_dict() for loan in loans])


# アプリケーション起動時にデータベースを作成
with app.app_context():
    if not os.path.exists(db_path):
        print("Creating database...")
        db.create_all()
        print("Database created.")

if __name__ == '__main__':
    app.run(debug=True)
