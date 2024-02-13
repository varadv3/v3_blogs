from flask import render_template, flash, redirect, url_for, request
from app import app, db, login
from .forms import LoginForm, RegistrationForm, EditProfileForm, FollowUnfollowForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from .models import User, Post
from sqlalchemy import select
from urllib.parse import urlsplit
from datetime import datetime, timezone
from .email import send_password_reset_email

#index page
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # print(4 / 0)
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.body.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post is live now!')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    
    # for pagination
    # posts = db.paginate(query, per_pages=[no of elements iterable you want], error_out=[error if range if out of bounds])
    posts = db.paginate(
        current_user.following_posts(), #it is a query having select
        per_page=app.config['POSTS_PER_PAGE'],
        page=page,
        error_out=False
    ) 
    #this db.paginate return and object of Paginate class from sqlalchemy

    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title="Home", posts=posts.items, form=form, next_url=next_url, prev_url=prev_url)

@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        select=select(Post).order_by(Post.timestamp.desc()), #it is a query having select
        per_page=app.config['POSTS_PER_PAGE'],
        page=page,
        error_out=False
    ) 
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items, next_url=next_url, prev_url=prev_url)
#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    #if authenticated person tries to access login page, it is not allowed, since he is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        #from database exact User with provided user name
        user = db.session.scalar(select(User).where(User.username == form.username.data))
        
        #if user not found or password didn't match
        if user is None or not user.check_password(form.password.data):
            flash('Invalid Username or Password, please check')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get('next')
        #checking if next query is relative url or not (then it's abs url which are not allowed)
        if not next_page or urlsplit(next_page).netloc != '': 
            return redirect(url_for('index'))
        return redirect(next_page)
        
    return render_template('login.html', title='Login', form=form)

#logout page
@app.route('/logout')
def logout():
    logout_user()
    flash('Successfully Logged out')
    return redirect(url_for('login'))

#register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    if current_user.is_authenticated:
        return redirect('index')
    form = RegistrationForm()
    
    if form.validate_on_submit():
        #add this user in db
        u = User(username=form.username.data, email=form.email.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        
        #login this user
        login_user(u)
        flash('Congrats! Account created successfully!')
        return redirect(url_for('index'))
    
    return render_template('register.html', form=form, title='Register')

#profile page
@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(select(User).where(User.username == username))
    form = FollowUnfollowForm()
    now = datetime.utcnow()
    last_seen = now - user.last_seen
    last_seen = int(last_seen.total_seconds() // 60)

    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        user.posts.select().order_by(Post.timestamp.desc()),
        per_page=app.config['POSTS_PER_PAGE'],
        page=page,
        error_out=False
    )

    next_url = url_for('user', username=username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=username, page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', 
        user=user, 
        posts=posts.items, 
        title='Profile', 
        form=form, 
        last_seen=last_seen,
        next_url=next_url,
        prev_url=prev_url
    )

#edit_profile page
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes has been saved')
        return redirect(url_for('user', username=current_user.username))
    elif request.method == 'GET':
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form, title='Edit Profile')

#storing last seen of user
@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@app.route('/follow/<username>', methods=['GET','POST'])
@login_required
def follow(username):
    form = FollowUnfollowForm()
    if form.validate_on_submit():
        #get the user
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            flash('User not found!')
            return redirect(url_for('index'))

        if user.username == current_user.username:
            flash("You can't follow yourself")
            return redirect(url_for('user', username=user))
        
        current_user.follow(user)
        db.session.commit()
        flash(f'You started following {username}!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = FollowUnfollowForm()
    if form.validate_on_submit():
        #get the user
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            flash('User not found!')
            return redirect(url_for('index'))

        if user.username == current_user.username:
            flash("You can't Unfollow yourself")
            return redirect(url_for('user', username=user))
        
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You are not following {username} now!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
            flash('Check you email for further instructions!')
            return redirect(url_for('login'))
        flash('''User with this email don't exist! First Register yourself please!''')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title='Reset Password Request', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset!')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token, form=form)