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
db_path = os.path.join(os.path.dirname(__file__), 'library.db')
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
    # メールアドレスを必須項目に変更
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email}

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    is_loaned = db.Column(db.Boolean, default=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'is_loaned': self.is_loaned,
            'borrower_id': self.borrower_id
        }

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=lambda: datetime.now(JST))
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    
    book = db.relationship('Book', backref=db.backref('loans', lazy=True))
    user = db.relationship('User', backref=db.backref('loans', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'user_id': self.user_id,
            'loan_date': self.loan_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'book_title': self.book.title,
            'user_name': self.user.name
        }

# --- APIエンドポイント (更新) ---

@app.route('/')
def index():
    return render_template('index.html')

# --- 認証API (更新) ---
@app.route('/api/register', methods=['POST'])
def register():
    """新規ユーザー登録"""
    data = request.json
    if not data.get('email'):
        return jsonify({'error': 'メールアドレスは必須です'}), 400
    if User.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'このユーザー名は既に使用されています'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'このメールアドレスは既に使用されています'}), 400
        
    new_user = User(name=data['name'], email=data['email'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return jsonify({'message': '登録が成功しました', 'user': new_user.to_dict()}), 201

@app.route('/api/login', methods=['POST'])
def login():
    """ログイン処理 (メールアドレスを使用)"""
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({'message': 'ログイン成功', 'user': user.to_dict()})
    return jsonify({'error': 'メールアドレスまたはパスワードが無効です'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'ログアウト成功'})

@app.route('/api/status')
def status():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True, 'user': current_user.to_dict()})
    else:
        return jsonify({'logged_in': False})

# --- 図書・貸出API (変更なし) ---
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Book.query.order_by(Book.title).all()
    return jsonify([book.to_dict() for book in books])

@app.route('/api/books', methods=['POST'])
@login_required
def add_book():
    data = request.json
    isbn = data.get('isbn') if data.get('isbn') else None
    if isbn and Book.query.filter_by(isbn=isbn).first():
        return jsonify({'error': 'このISBNは既に使用されています'}), 400
    new_book = Book(title=data['title'], author=data['author'], isbn=isbn)
    db.session.add(new_book)
    db.session.commit()
    return jsonify(new_book.to_dict()), 201

@app.route('/api/loan', methods=['POST'])
@login_required
def loan_book():
    data = request.json
    book_id = data['book_id']
    book = Book.query.get(book_id)
    if not book or book.is_loaned:
        return jsonify({'error': 'この本は現在貸出できません'}), 400
    now = datetime.now(JST)
    due_date = now + timedelta(weeks=2)
    book.is_loaned = True
    book.borrower_id = current_user.id
    new_loan = Loan(book_id=book.id, user_id=current_user.id, loan_date=now, due_date=due_date)
    db.session.add(new_loan)
    db.session.commit()
    return jsonify(new_loan.to_dict()), 201

@app.route('/api/return/<int:book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    book = Book.query.get(book_id)
    if not book or not book.is_loaned:
        return jsonify({'error': 'この本は貸出中ではありません'}), 400
    loan = Loan.query.filter_by(book_id=book.id, return_date=None).first()
    if not loan:
        return jsonify({'error': '貸出記録が見つかりません'}), 404
    if loan.user_id != current_user.id:
        return jsonify({'error': 'この本を返却する権限がありません'}), 403
    book.is_loaned = False
    book.borrower_id = None
    loan.return_date = datetime.now(JST)
    db.session.commit()
    return jsonify(loan.to_dict())

@app.route('/api/loans', methods=['GET'])
@login_required
def get_loans():
    loans = Loan.query.order_by(Loan.loan_date.desc()).all()
    return jsonify([loan.to_dict() for loan in loans])

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

