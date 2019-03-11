from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityLike import EntityLike
from each.Prop.PropBase import PropBase

from each.db import DBConnection

Base = declarative_base()


class PropLike(PropBase, Base):
    __tablename__ = 'each_prop_like'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid):
        with DBConnection() as session:
            return [_[1].to_dict() for _ in session.db.query(cls, EntityLike).
                    filter(cls.eid == eid).
                    filter(cls.propid == propid).
                    filter(cls.value == EntityLike.eid).all()]

    @classmethod
    def get_like_user_related(cls, eid, propid, userid):
        with DBConnection() as session:
            return [_[1].to_dict() for _ in session.db.query(cls, EntityLike).
                    filter(cls.eid == eid).
                    filter(cls.propid == propid).
                    filter(cls.value == EntityLike.eid).
                    filter(EntityLike.userid == userid).all()]

    @classmethod
    def delete(cls, eid, propid, raise_exception=True):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid, propid=propid).all()
            if len(res):
                [[EntityLike.delete(_.value), session.db.delete(_)] for _ in res]
                session.db.commit()
            elif raise_exception:
                raise FileNotFoundError('(eid, propid)=(%i, %i) was not found' % (eid, propid))
