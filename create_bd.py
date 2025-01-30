import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_name = sq.Column(sq.String(40), unique=True)
    chat_id = sq.Column(sq.Integer, nullable=False)

    progress = relationship('UserProgress', back_populates= 'user')
    words = relationship('Word',back_populates='user')

class Word(Base):
    __tablename__ = 'words'
    words_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    words_ru = sq.Column(sq.String(40), nullable=False)
    words_en = sq.Column(sq.String(40), nullable=False)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.user_id'))

    progress = relationship('UserProgress', back_populates='word')
    user = relationship('User', back_populates= 'words')

class UserProgress(Base):
    __tablename__ = 'user_progress'
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.user_id'), nullable=False)
    words_id = sq.Column(sq.Integer, sq.ForeignKey('words.words_id'), nullable=False)
    is_learned = sq.Column(sq.Boolean, default=False)

    user = relationship('User', back_populates='progress')
    word = relationship('Word', back_populates='progress')

def create_tables(engine):
    #Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
