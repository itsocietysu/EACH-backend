import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityProp import EntityBase
from each.Entities.EntityProp import EntityProp

from each.db import DBConnection
from each.utils import isAllInData

Base = declarative_base()


class EntityComment(EntityBase, Base):
    __tablename__ = 'each_comment'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    userid = Column(Integer)
    text = Column(String)
    created = Column(Date)

    json_serialize_items_list = ['eid', 'userid', 'text', 'created']

    def __init__(self, userid, text):
        super().__init__()

        self.userid = userid
        self.text = text

        ts = time.time()
        self.created = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data, prop):

        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        if isAllInData(['text', 'userid', 'id'], data):
            text = data['text']
            userid = data['userid']
            _id = data['id']

            from each.Prop.PropComment import PropComment
            comments = PropComment.get_comment_user_related(_id, PROPNAME_MAPPING[prop], userid)

            if not len(comments):
                new_entity = EntityComment(userid, text)
                eid = new_entity.add()

                PropComment(_id, PROPNAME_MAPPING[prop], eid).add()

            else:
                eid = comments[0]['eid']

        return eid

    @classmethod
    def update_from_json(cls, data, prop):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        if isAllInData(['userid', 'id'], data):
            userid = data['userid']
            _id = data['id']

            from each.Prop.PropComment import PropComment
            with DBConnection() as session:
                comments = session.db.query(PropComment, EntityComment).filter(PropComment.eid == _id). \
                    filter(PropComment.propid == PROPNAME_MAPPING[prop]). \
                    filter(PropComment.value == EntityComment.eid).filter(EntityComment.userid == userid).all()

                if len(comments):
                    eid = comments[0][0].value
                    if 'text' in data:
                        for _ in comments:
                            setattr(_[1], 'text', data['text'])
                        session.db.commit()

        return eid
