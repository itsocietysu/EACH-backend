import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityProp import EntityBase
from each.Entities.EntityProp import EntityProp

from each.db import DBConnection

Base = declarative_base()

class EntityComment(EntityBase, Base):
    __tablename__ = 'each_comment'


    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    userid = Column(Integer)
    text = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'userid', 'text', 'created', 'updated']

    def __init__(self, userid, text):
        super().__init__()

        self.userid = userid
        self.text = text

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data, userId):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        if 'text' in data and 'eid' in data:
            text = data['text']
            eid = data['eid']

            new_entity = EntityComment(userId, text)
            _id = new_entity.add()

            from each.Prop.PropComment import PropComment
            PropComment(eid, PROPNAME_MAPPING["comment"], _id).add()

        return _id

    @classmethod
    def update_from_json(cls, data):
        eid = None

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityComment).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'text' in data:
                            _.text = data['text']

                        session.db.commit()

        return eid

