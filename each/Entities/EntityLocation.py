from sqlalchemy import Column, String, Integer, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.db import DBConnection

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

    @classmethod
    def add_from_json(cls, data):

        eid = None

        if 'name' in data and 'latitude' in data and 'longitude' in data:

            name = data['name']
            longitude = data['longitude']
            latitude = data['latitude']

            new_entity = EntityLocation(name, latitude, longitude)
            eid = new_entity.add()

        return eid

    @classmethod
    def delete(cls, eid):
        from each.Prop.PropLocation import PropLocation
        PropLocation.delete_value(eid, False)
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid).all()

            if len(res):
                [session.db.delete(_) for _ in res]
                session.db.commit()
            else:
                raise FileNotFoundError('%s was not found' % cls.__name__)
