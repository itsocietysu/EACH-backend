from sqlalchemy import Column, String, Integer, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.db import DBConnection

Base = declarative_base()

class EntityProp(EntityBase, Base):
    __tablename__ = 'each_prop'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    name = Column(String)
    type = Column(String)

    json_serialize_items_list = ['eid', 'name', 'type']

    def __init__(self, name, type):
        super().__init__()
        self.name = name
        self.type = type

    @classmethod
    def map_name_id(cls):
        with DBConnection() as session:
            return {_.name: _.eid for _ in session.db.query(cls).all()}

    @classmethod
    def map_id_name(cls):
        with DBConnection() as session:
            return {_.eid: _.name for _ in session.db.query(cls).all()}
