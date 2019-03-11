import datetime
import os
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.db import DBConnection

Base = declarative_base()

class EntityMedia(EntityBase, Base):
    __tablename__ = 'each_media'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    ownerid = Column(Integer)
    name = Column(String)
    desc = Column(String)
    type    = Column(String)
    url     = Column(Integer)
    created = Column(Date)

    json_serialize_items_list = ['eid', 'ownerid', 'name', 'desc', 'type', 'url', 'created']

    def __init__(self, ownerid, type, url, name='', desc=''):
        super().__init__()

        self.ownerid = ownerid
        self.name = name
        self.desc = desc
        self.type = type
        self.url = url

        ts = time.time()
        self.created = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def delete(cls, eid):
        def safe_delete(item):
            if os.path.isfile(item.url):
                os.remove(item.url)
            session.db.delete(item)

        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid).all()

            if len(res) == 1:
                [safe_delete(_) for _ in res]
                session.db.commit()
            else:
                raise FileNotFoundError('%s was not found' % cls.__name__)
