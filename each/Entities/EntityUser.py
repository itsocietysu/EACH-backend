import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase

Base = declarative_base()

class EntityUser(EntityBase, Base):
    __tablename__ = 'each_user'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    type = Column(String, primary_key=True)
    login = Column(String)
    email = Column(String, primary_key=True)
    image = Column(String)
    access_type = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'type', 'login', 'email', 'image',
                                 'access_type', 'created', 'updated']

    def __init__(self, type, login, email, image, access_type):
        super().__init__()

        self.type = type
        self.login = login
        self.email = email
        self.image = image
        self.access_type = access_type

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    def update_user(self, data):

        if ('login' in data):
            self.login = data['login']
        if ('email' in data):
            self.email = data['email']
        if ('image' in data):
            self.image = data['image']
        if ('access_type' in data):
            self.access_type = data['access_type']
