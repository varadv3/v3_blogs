from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Column, Integer, func, select, or_
from sqlalchemy.orm import Mapped, mapped_column, WriteOnlyMapped, relationship, aliased
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from hashlib import md5
from app import app
import jwt
from time import time


followers = db.Table(
    'followers',
    db.metadata,
    Column('follower_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('followed_id', Integer, ForeignKey('user.id'), primary_key=True)
)
class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    email: Mapped[str] = mapped_column(String(120), index=True, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))
    posts: WriteOnlyMapped['Post'] = relationship(back_populates='author')
    about_me: Mapped[Optional[str]] = mapped_column(String(140))
    last_seen: Mapped[Optional[datetime]] = mapped_column(default= lambda:datetime.now(timezone.utc))

    #list of users (kind a table) which are followed by this user
    following: WriteOnlyMapped['User'] = relationship(
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates='followers'
    )

    #list of users (kind a table) which are followers of this user
    followers: WriteOnlyMapped['User'] = relationship(
        secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following'
    )

    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=retro&s={size}"
    
    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None
    
    #follow a user
    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    #unfollow a user
    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    #count of users who follow this user
    def followers_count(self):
        query = select(func.count()).select_from(
            self.followers.select().subquery()
        )
        return db.session.scalar(query)
    
    #count of users followed by this user
    def following_count(self):
        query = select(func.count()).select_from(
            self.following.select().subquery()
        )
        return db.session.scalar(query)
    
    def following_posts(self):
        Author = aliased(User)
        Follower = aliased(User)
        return (
            select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )
    
    def get_reset_password_token(self, expires_in=600):
        token = jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')['reset_password']
        except:
            return None
        return db.session.get(User, id)

class Post(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(140))
    timestamp: Mapped[datetime] = mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    author: Mapped[User] = relationship(back_populates='posts')

    def __repr__(self):
        return f"<Posted by {self.user_id} on {self.timestamp}>"

@login.user_loader
def login_user(id):
    return db.session.get(User, int(id))