import sqlalchemy as sq
#from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import configparser
from create_bd import create_tables, Word
config = configparser.ConfigParser()
config.read('settings.ini')
password = config["password"]['password']

DSN = f'postgresql://postgres:{password}@localhost:5432/EngTchDZ'
engine = sq.create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()
create_tables(engine)

word1 = Word(words_ru='Мир', words_en='peace')
word2 = Word(words_ru='иметь', words_en='have')
word3 = Word(words_ru='здесь', words_en='here')
word4 = Word(words_ru='с', words_en='with')
word5 = Word(words_ru='туалет', words_en='toilet')
word6 = Word(words_ru='вместе', words_en='together')
word7 = Word(words_ru='река', words_en='river')
word8 = Word(words_ru='они', words_en='they')
word9 = Word(words_ru='трогать', words_en='touch')
word10 = Word(words_ru='значение', words_en='value')
word11 = Word(words_ru='или', words_en='or')
word12 = Word(words_ru='и', words_en='and')
word13 = Word(words_ru='если', words_en='if')
word14 = Word(words_ru='для', words_en='for')
word15 = Word(words_ru='переменная', words_en='variable')
word16 = Word(words_ru='в', words_en='in')
word17 = Word(words_ru='буква', words_en='word')

session.add_all([word1, word2, word3, word4, word5, word6,
                 word7, word8, word9, word10, word11, word12,
                 word13, word14, word15, word16, word17])
session.commit()
session.close()