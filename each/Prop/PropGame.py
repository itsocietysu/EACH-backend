from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base

from each.db import DBConnection

from each.Entities.EntityGame import EntityGame

Base = declarative_base()

class PropGame(PropBase, Base):
    __tablename__ = 'each_prop_game'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, items=[]):
        with DBConnection() as session:
            return [_[1].to_dict(items) for _ in session.db.query(cls, EntityGame).
                filter(cls.eid == eid).
                filter(cls.propid == propid).
                filter(cls.value == EntityGame.eid).all()]