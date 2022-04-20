##############################################################################################
#                                                                                            #
#                               PACKAGES                                                     #
#                                                                                            #
##############################################################################################

# from tkinter import image_types
from socket import RDS_CMSG_RDMA_ARGS
from winreg import REG_REFRESH_HIVE
from flask import Flask, redirect, render_template, request, url_for, flash
from flask_wtf import FlaskForm
from sqlalchemy import desc
from wtforms import StringField, PasswordField, SubmitField, DateField, HiddenField
from wtforms.validators import InputRequired, Length
from flask_login import LoginManager, login_user, login_required, UserMixin, current_user, logout_user, user_accessed
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_wtf.file import FileField, FileRequired, FileAllowed
from jinja2 import StrictUndefined
from flask_sqlalchemy import SQLAlchemy


from datetime import date

import os
import uuid
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
db = SQLAlchemy()


UPLOAD_FOLDER = 'static/uploads/'

UNAME = os.getenv("UNAME")
PWD = os.getenv("PWD")
DATABASE_URL = os.environ.get('DATABASE_URL')

# app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{UNAME}:{PWD}@localhost/account" or os.environ.get('DATABASE_URL')
app.config[DATABASE_URL]
# app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://ofvzknqhbuvmyb:89071732f91e52ee4884f1a9a76dba51481267665bbfbcca86dab5f15aae8a9b@ec2-3-229-252-6.compute-1.amazonaws.com:5432/d1i63ch8v52drc"
# SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
db.app = app
db.init_app(app)


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
bcrypt = Bcrypt(app)
app.secret_key = "ABC"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 4MB max-limit.
app.config['ALLOWED_IMAGE_EXTENSION'] = ["PNG", "JPEG", "JPG", "GIF"]

app.jinja_env.undefined = StrictUndefined

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return FormUser.query.get(int(user_id))

##############################################################################
#                                                                            #
#                         DATABASE                                           #
#                                                                            #
##############################################################################


class FormUser(db.Model, UserMixin):
    
    __tabelname__ = "form_user"
    
    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(250), nullable=True)

    def get_id(self):
        return (self.user_id)

    def __repr__(self):
        return f"<FormUser user_id={self.user_id} email={self.email} password={self.password}>"

class Image(db.Model):
    
    __tabelname__ = "images"
    
    img_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("form_user.user_id"))
    img_name = db.Column(db.String(300), nullable=True)
    title = db.Column(db.String(150))
    note = db.Column(db.String(500))
    date = db.Column(db.DateTime)
    
    
    formuser = db.relationship("FormUser", backref=db.backref("images"))
    
    def __repr__(self):
        return f"<Image img_id={self.img_id} user_id={self.user_id} img_name={self.img_name} title={self.title} note={self.note} date={self.date}>"


##############################################################################
#                                                                            #
#                         FLASKFORM                                          #
#                                                                            #
##############################################################################
class SignupForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=2, max=25)], render_kw={"placeholder":"Username"})
    email = StringField(validators=[InputRequired(), Length(min=2, max=30)], render_kw={"placeholder":"Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=15)], render_kw={"placeholder":"Password"})
    submit = SubmitField("Sign Up")


# #CHECK IF USERNAME ALREADY EXSISTS
    def check_email(self):
        existing_user_email = FormUser.query.filter_by(email = self.email.data).first()
        if existing_user_email:
            return True
        else:
            return False
        
class LoginForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=2, max=30)], render_kw={"placeholder":"Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=50)], render_kw={"placeholder":"Password"})
    submit = SubmitField("Login")

class PhotoForm(FlaskForm):
    photo = FileField(validators=[FileRequired('Empty file'),FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    title = StringField(Length(max=50), render_kw={"placeholder":"Title"})
    note =  StringField(Length(max=200), render_kw={"placeholder":"Note"})
    date = DateField(validators=[InputRequired('Date')])
    submit = SubmitField('Upload')

class UpdateForm(FlaskForm):
    title = StringField(Length(max=50), render_kw={"placeholder":"Title"})
    note =  StringField(Length(max=200), render_kw={"placeholder":"Note"})
    date = DateField('Date')
    image_id = HiddenField("image_id")
    submit = SubmitField('Update')


@app.route("/", methods=['GET','POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if form.check_email():
            flash('Email already exists!')
            return render_template("signup.html", form=form)
        else:
            pw_hash= bcrypt.generate_password_hash(form.password.data).decode('utf8')
            
            new_user = FormUser(username=form.username.data, email=form.email.data, password=pw_hash)
            db.session.add(new_user)
            db.session.commit()
            flash('Your registration was successful')
        return redirect(url_for('login'))
    
    return render_template("signup.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = FormUser.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("main"))
            else:
                flash("Wrong password...Try again and good luck!")
        else:
            flash("That email doesn't exists!")
    return render_template('login.html', form=form)       


@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():
    form = PhotoForm()
    updateform = UpdateForm()
    if form.validate_on_submit():
        f = form.photo.data
        img_data = form.data
        
        # filename = secure_filename(f.filename
        filename = 'img_' + str(uuid.uuid4()) + '.jpg'    
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_img = Image(user_id=current_user.user_id, 
                img_name=filename, 
                title=img_data['title'], 
                note=img_data['note'],
                date=img_data['date'])
        
        db.session.add(new_img)
        db.session.commit()
        
        flash("Memory succesfully uploaded!")
        return redirect(url_for('main'))
    
    images = Image.query.filter_by(user_id=current_user.user_id)
    return render_template('main.html', form=form, updateform=updateform, images=images) 
    
    

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    updateform = UpdateForm()  
    image_to_update = Image.query.get(id)
    if request.method == "POST":
        if request.form['title'] != '':
            image_to_update.title = request.form['title']
        if request.form['note'] != '':
            image_to_update.note = request.form['note']
        if request.form['date'] != '':
            image_to_update.date = request.form['date']

        try:
            db.session.commit()
            flash('Image Updated!')
            return redirect(url_for('main'))
            # return render_template('main.html', form=form, image_to_update=image_to_update)
        
        except:
            flash('Error')
            return render_template('main.html', updateform=updateform, image_to_update=image_to_update)
        
    
    images = Image.query.filter_by(user_id=current_user.user_id)
    return render_template('main.html', updateform=updateform, images=images)
    

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    my_data = Image.query.get(id)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], my_data.img_name))
    db.session.delete(my_data)
    db.session.commit()
    flash("Memory deleted!")
    
    return redirect(url_for('main'))
    

@app.route('/logout', methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    flash("You are now logged out!")
    return redirect(url_for('login'))


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    # make sure templates, etc. are not cached in debug mode
    app.jinja_env.auto_reload = app.debug
    app.run()