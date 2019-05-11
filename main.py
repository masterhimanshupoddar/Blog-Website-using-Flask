# set FLASK_APP=main.py
# set FLASK_DEBUG=1
# flask run

from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, RadioField, SelectField
from wtforms.validators import InputRequired, EqualTo
from datetime import datetime
from flask_mail import Mail
import json
import os
from werkzeug import secure_filename
import math

with open("config.json",encoding='utf-8') as c:
    params = json.load(c)['params']
local_server = True
app = Flask(__name__)
app.secret_key = 'secret-key'
app.config.update(
MAIL_SERVER = 'smtp.gmail.com',
MAIL_PORT = '465',
MAIL_USE_SSL = True,
MAIL_USERNAME = params['gmail-user'],
MAIL_PASSWORD = params['gmail-password']
)
app.config['UPLOAD_FOLDER'] = params['location']

mail = Mail(app)

if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']


db = SQLAlchemy(app)


class Contacts(db.Model):
    '''
    sno, phno, msg, date, email
    '''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    phone_num = db.Column(db.String(13),nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21),nullable=False)
    content = db.Column(db.String(1200), nullable=False)
    tagline = db.Column(db.String(1200), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(15), nullable=True)

class Admin(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(21),nullable=False)

class MyForm(FlaskForm):
    name = StringField('Email', validators=[InputRequired(message="This field cannot be empty")])
    password = PasswordField('Password', validators=[InputRequired(message="This field cannot be empty")])
    confirm = PasswordField('Password', validators=[InputRequired(message="This field cannot be empty"), EqualTo('password', message='Passwords must match')])

@app.route("/")
def home():

    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_post']))
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page=1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_post']):(page-1)*int(params['no_of_post'])+int(params['no_of_post'])]

    # pagination
    # first page
    if page==1:
        prev = "#"
        next = "/?page=" + str(page+1)
    elif(page == last):
        prev = "/?page=" + str(page-1)
        next = "#"
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/about")
def about():
    return render_template('about.html', params=params)



@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if request.method == 'POST':
        '''
        Add entry to the database
        '''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        # arg name should be same as column names and rhs should be same variable as above in which we are fetching input
        entry = Contacts(name=name, phone_num=phone, msg=message, email=email, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message from '+name,
        sender=email,
        recipients=[params['gmail-user']],
        body = message + "\n" + phone )
        flash("Thanks, We will get back to you soon", 'success')
    return render_template('contact.html')


@app.route("/admin-reg",  methods=['GET', 'POST'])
def adminreg():
    form= MyForm()
    if form.validate_on_submit():
        '''
        Add entry to the database
        '''
        # arg name should be same as column names and rhs should be same variable as above in which we are fetching input
        entry = Admin(name = form.name.data, password = form.password.data)
        db.session.add(entry)
        db.session.commit()
        flash("Thanks, For registering", 'success')
    return render_template('admin-reg.html', form=form)

@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route("/dashboard",  methods=['GET', 'POST'])
def dashboard():
    posts = Posts.query.all()

    if 'user' in session and session['user']==params['admin_user']:
        return render_template('dashboard.html', params=params, posts=posts)


    if request.method=='POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        form_data = Admin.query.filter_by(name=username).first()
        #if username==params['admin_user'] and userpass==params['admin_password']:
        if form_data!=None and username==form_data.name and userpass==form_data.password:
            # set the session variable
            session['user'] = username
            return render_template('dashboard.html', params=params, posts=posts)
        else:
            return render_template('login.html', params=params)




    else:
        return render_template('login.html', params=params)


@app.route("/edit/<string:sno>",  methods=['GET', 'POST'])
def edit(sno):
    if request.method == 'GET':
        if sno == "0":
            post = Posts(sno=0,
            title="",
            slug="",
            content="",
            tagline="",
            date = "",
            img_file="" )
            return render_template('edit.html', params=params, post=post)
        else:
            post = Posts.query.filter_by(sno=sno).first()
            return render_template('edit.html', params=params, post=post)
    if request.method=='POST':
        if 'user' in session and session['user']==params['admin_user']:
            serialno =len(Posts.query.all())+1
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('image_file')
            date = datetime.now()

            # This end point 0 is to add new post
            if sno=='0':
                post = Posts(sno=serialno,
                title=box_title,
                slug=slug,
                content=content,
                tagline=tline,
                date = date,
                img_file=img_file )
                db.session.add(post)
                db.session.commit()

                return render_template('edit.html', params=params, post=post)

            else:
                post = Posts.query.filter_by(sno=int(sno)).first()
                post.title=box_title
                post.slug=slug
                post.content=content
                post.tagline=tline
                post.date = date
                post.img_file=img_file
                db.session.add(post)
                db.session.commit()
                return redirect('/edit/'+sno)

        return render_template('edit.html', params=params, post=post)

@app.route("/uploader",  methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user']==params['admin_user']:
        if (request.method=='POST'):
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
            return "Uploaded Successfully"

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/delete/<string:sno>",  methods=['GET', 'POST'])
def delete_post(sno):
    if 'user' in session and session['user']==params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')
