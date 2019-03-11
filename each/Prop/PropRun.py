from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base

from each.db import DBConnection

from each.Entities.EntityRun import EntityRun

Base = declarative_base()


class PropRun(PropBase, Base):
    __tablename__ = 'each_prop_run'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, items=[]):
        with DBConnection() as session:
            return [_[1].to_dict(items) for _ in session.db.query(cls, EntityRun).
                    filter(cls.eid == eid).
                    filter(cls.propid == propid).
                    filter(cls.value == EntityRun.eid).all()]

    @classmethod
    def delete_value(cls, value, raise_exception=True):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(value=value).all()

            if len(res):
                EntityRun.delete(value)
                [session.db.delete(_) for _ in res]
                session.db.commit()
            else:
                if raise_exception:
                    raise FileNotFoundError('(value)=(%s) was not found' % str(value))
