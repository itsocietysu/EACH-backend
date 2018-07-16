from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityPost import EntityPost
from each.Prop.PropBase import PropBase

Base = declarative_base()

from each.db import DBConnection

class PropPost(PropBase, Base):
    __tablename__ = 'each_prop_post'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, items=[]):
        with DBConnection() as session:
            res = []
            for _ in session.db.query(cls, EntityPost).\
                filter(cls.eid == eid).\
                filter(cls.propid == propid).\
                filter(cls.value == EntityPost.eid).all():

                obj_dict = _[1].to_dict(['eid', 'description'])
                obj_dict.update(EntityPost.get_wide_object(_[1].eid, items))
                res.append(obj_dict)

            return res