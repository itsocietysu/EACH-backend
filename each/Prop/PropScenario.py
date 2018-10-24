from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base

from each.db import DBConnection

from each.Entities.EntityScenario import EntityScenario

Base = declarative_base()


class PropScenario(PropBase, Base):
    __tablename__ = 'each_prop_scenario'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, items=[]):
        with DBConnection() as session:
            return [_[1].to_dict(items) for _ in session.db.query(cls, EntityScenario).
                    filter(cls.eid == eid).
                    filter(cls.propid == propid).
                    filter(cls.value == EntityScenario.eid).all()]

    @classmethod
    def delete(cls, eid, propid, raise_exception=True):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid, propid=propid).all()
            if len(res):
                [[EntityScenario.delete(_.value), session.db.delete(_)] for _ in res]
                session.db.commit()
            elif raise_exception:
                raise FileNotFoundError('(eid, propid)=(%i, %i) was not found' % (eid, propid))
