from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityMedia import EntityMedia
from each.Prop.PropBase import PropBase

Base = declarative_base()

from each.db import DBConnection

class PropMedia(PropBase, Base):
    __tablename__ = 'each_prop_media'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)

    @classmethod
    def get_object_property(cls, eid, propid, items=[]):
        with DBConnection() as session:
            return [_[1].to_dict(items) for _ in session.db.query(cls, EntityMedia).
                filter(cls.eid == eid).
                filter(cls.propid == propid).
                filter(cls.value == EntityMedia.eid).all()]



    '''
    def deleteList(cls, eid, propid, listIDs, session=None, raise_exception=True):
        if session:
            # TODO: Look it
            res = session.db.query(cls).filter_by(eid=eid, propid=propid).all()

            if len(res):
                [session.db.delete(_) for _ in res if _.value in listIDs]
                session.db.commit()
            else:
                if raise_exception:
                    raise FileNotFoundError('(eid, propid)=(%i, %i) was not found' % (eid, propid))
    '''

    @classmethod
    def delete(cls, eid, propid, session=None, raise_exception=True):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid, propid=propid).all()
            if len(res):
                [[EntityMedia.delete(_.value), session.db.delete(_)] for _ in res]
                session.db.commit()
            elif raise_exception:
                raise FileNotFoundError('(eid, propid)=(%i, %i) was not found' % (eid, propid))
