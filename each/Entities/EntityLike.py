import datetime
import time

from sqlalchemy import Column, Date, Integer, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp

from each.db import DBConnection
from each.utils import isAllInData

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
    def add_from_json(cls, data, prop):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        if isAllInData(['weight', 'userid', 'id', 'prop_like'], data):
            weight = data['weight']
            userid = data['userid']
            _id = data['id']

            from each.Prop.PropLike import PropLike
            likes = PropLike.get_like_user_related(_id, PROPNAME_MAPPING[prop], userid)

            if not len(likes):
                new_entity = EntityLike(userid, weight)
                eid = new_entity.add()

                PropLike(_id, PROPNAME_MAPPING[prop], eid).add()

            else:
                eid = likes[0]['eid']

        return eid

