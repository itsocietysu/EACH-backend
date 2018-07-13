import datetime
import time

from sqlalchemy import Column, Date, Integer, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp

from each.db import DBConnection

Base = declarative_base()

class EntityLike(EntityBase, Base):
    __tablename__ = 'each_like'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    userid = Column(Integer)
    created = Column(Date)
    weight = Column(Integer)

    json_serialize_items_list = ['eid', 'userid', 'created', 'weight']

    def __init__(self, userid, weight):
        super().__init__()

        self.userid = userid
        ts = time.time()
        self.created = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        self.weight = weight

    @classmethod
    def add_from_json(cls, data, userId):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        _id = None
        if 'weight' in data and 'eid' in data:
            weight = data['weight']
            eid = data['eid']

            from each.Prop.PropLike import PropLike
            likes = PropLike.get_post_user_related(eid, PROPNAME_MAPPING['like'], userId)

            if not len(likes):
                new_entity = EntityLike(userId, weight)
                _id = new_entity.add()

                PropLike(eid, PROPNAME_MAPPING['like'], _id).add()

        return _id


    @classmethod
    def update_from_json(cls, data):
        eid = None

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityLike).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'weight' in data:
                            _.weight = data['weight']

                        session.db.commit()

        return eid




