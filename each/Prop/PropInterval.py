from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base

from each.db import DBConnection
from each.utils import _interval_to_string

Base = declarative_base()


class PropInterval(PropBase, Base):
    __tablename__ = 'each_prop_interval'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, session=None):
        def proceed(session):
            return [_interval_to_string(_.value) for _ in session.db.query(cls).filter_by(eid=eid, propid=propid).all()]

        if session:
            return proceed(session)

        with DBConnection() as session:
            return proceed(session)
