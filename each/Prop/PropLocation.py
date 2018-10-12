from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityLocation import EntityLocation
from each.Prop.PropBase import PropBase

Base = declarative_base()

from each.db import DBConnection

class PropLocation(PropBase, Base):
    __tablename__ = 'each_prop_location'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid):
        with DBConnection() as session:
            return [_[1].to_dict() for _ in session.db.query(cls, EntityLocation).
                filter(cls.eid == eid).
                filter(cls.propid == propid).
                filter(cls.value == EntityLocation.eid).all()]

    @classmethod
    def get_object_in_area(cls, propid, p, r):
        with DBConnection() as session:
            return [_[0] for _ in session.db.query(cls, EntityLocation)
                .filter(cls.propid == propid)
                .filter(EntityLocation.longitude.between(p[1] - r, p[1] + r))
                .filter(EntityLocation.latitude.between(p[0] - r, p[0] + r))
                .filter(cls.value == EntityLocation.eid)
                .all()]

    @classmethod
    def delete_by_value(cls, eid, propid, value, raise_exception=True):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid, propid=propid, value=value).all()

            if len(res):
                [session.db.delete(_) for _ in res]
                session.db.commit()
            else:
                if raise_exception:
                    raise FileNotFoundError('(eid, propid, value)=(%i, %i, %i) was not found' % (eid, propid, value))
