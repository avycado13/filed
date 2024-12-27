import random
import string
import os
from flask import Flask, request, send_from_directory, abort, render_template
from flask_sqlalchemy import SQLAlchemy
# TODO Unify login for all services
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, roles_required
from werkzeug.utils import secure_filename


def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app.db'
app.config['SECRET_KEY'] = generate_random_string(12)
app.config['USER_ENABLE_EMAIL'] = False

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    roles = db.relationship('Role', secondary='user_roles',
                            backref=db.backref('users', lazy='dynamic'))


class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


class UserRoles(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey(
        'user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey(
        'role.id', ondelete='CASCADE'))


db_adapter = SQLAlchemyAdapter(db, User)
user_manager = UserManager(db_adapter, app)


def assign_role_to_user(user, role_name):
    role = Role.query.filter_by(name=role_name).first()
    if role:
        user.roles.append(role)
        db.session.commit()


@app.route('/upload', methods=['POST'])
@login_required
@roles_required('admin')
def upload_file():
    if 'file' not in request.files:
        abort(400, description="No file part in the request.")
    file = request.files['file']
    if file.filename == '':
        abort(400, description="No file selected for uploading.")
    filename = secure_filename(file.filename)
    file.save(os.path.join('uploads', filename))
    return 'File uploaded successfully'


@app.route('/download/<filename>', methods=['GET'])
@login_required
def download_file(filename):
    if os.path.exists('uploads/' + filename):
        return send_from_directory('uploads', filename)
    abort(404, description="File not found.")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = user_manager.register_view()
        if User.query.count() == 1:
            assign_role_to_user(user, 'admin')
        return user
    return user_manager.register_view()


@app.route('/login', methods=['GET', 'POST'])
def login():
    return user_manager.login_view()

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_panel():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        role_name = request.form.get('role_name')
        user = User.query.get(user_id)
        if user:
            assign_role_to_user(user, role_name)
    users = User.query.all()
    return render_template('admin.html', users=users)


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
