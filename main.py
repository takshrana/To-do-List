from flask import Flask, render_template, url_for, request, redirect, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from functools import wraps
from forms import RegisterForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
import os


app = Flask(__name__)
Bootstrap5(app)
login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", 'sqlite:///todo.db')
db = SQLAlchemy()
db.init_app(app)


class TodoUser(db.Model, UserMixin):
    __tablename__ = "todo_user_table"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    todo = relationship("Todo", back_populates="user")


class Todo(db.Model):
    __tablename__ = "todo_list"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey("todo_user_table.id"))

    user = relationship("TodoUser", back_populates="todo")


def user_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return function(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(TodoUser, user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        if db.session.execute(db.select(TodoUser).filter_by(email=form.email.data)).scalar():
            flash("Email already registered.")
        else:
            saltPass = generate_password_hash(password=form.password.data, method='pbkdf2:sha256', salt_length=8)

            new_user = form.email.data
            user = TodoUser(email=new_user,password=saltPass)

            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))

    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(TodoUser).filter_by(email=form.email.data)).scalar()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash("Wrong password. Try Again.")
        else:
            flash("Email does not exist, pls register.")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
@user_required
@login_required
def index():
    todo_list = current_user.todo
    return render_template('index.html', todo_list=todo_list)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/add', methods=['POST'])
@user_required
@login_required
def add():
    title = request.form.get('title').strip()
    if title:
        new_todo = Todo(title=title, complete=False, user_id=current_user.id)
        db.session.add(new_todo)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/update/<int:id>')
@user_required
@login_required
def update(id):
    todo = Todo.query.filter_by(id=id).first()
    todo.complete = not todo.complete
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
@user_required
@login_required
def delete(id):
    todo = Todo.query.filter_by(id=id).first()
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
