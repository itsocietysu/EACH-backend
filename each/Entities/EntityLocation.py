from sqlalchemy import Column, String, Integer, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase

Base = declarative_base()

class EntityLocation(EntityBase, Base):
    __tablename__ = 'each_location'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    json_serialize_items_list = ['eid', 'name', 'latitude', 'longitude']

    def __init__(self, name, latitude, longitude):
        super().__init__()

        self.name = name
        self.latitude = latitude
        self.longitude = longitude