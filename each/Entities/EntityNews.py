from collections import OrderedDict
import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp

from each.Prop.PropLocation import PropLocation
from each.Prop.PropComment import PropComment
from each.Prop.PropLike import PropLike
from each.Prop.PropMedia import PropMedia

from each.db import DBConnection

Base = declarative_base()


class EntityNews(EntityBase, Base):
    __tablename__ = 'each_news'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    title = Column(String)
    text = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'title', 'text', 'created', 'updated']

    def __init__(self, title, text):
        super().__init__()

        self.title = title
        self.text = text

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data):
        eid = None

        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'image':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'image', _uid, _eid, _id, _val)
        }

        if 'title' in data and 'text' in data and "prop" in data:
            title = data['title']
            text = data['text']

            new_entity = EntityNews(title, text)
            eid = new_entity.add()

            try:
                with DBConnection() as session:
                    for prop_name, prop_val in data['prop'].items():
                        if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                            PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val, eid)
                        else:
                            EntityNews.delete(eid)
                            raise Exception('{%s} not existed property\nPlease use one of:\n%s' %
                                        (prop_name, str(PROPNAME_MAPPING)))

                    session.db.commit()
            except Exception as e:
                EntityNews.delete(eid)
                raise Exception('Internal error')

        return eid

    @classmethod
    def update_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'image':
                lambda s, _eid, _id, _val:
                PropMedia(_eid, _id, _val).update(session=s)
                if len(PropMedia.get().filter_by(eid=_eid, propid=_id).all())
                else PropMedia(_eid, _id, _val).add(session=session)
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityNews).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'title' in data:
                            _.title = data['title']

                        if 'text' in data:
                            _.text = data['text']

                        session.db.commit()

                        for prop_name, prop_val in data['prop'].items():
                            if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                                PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val)

                        session.db.commit()

        return eid

    @classmethod
    def get_wide_object(cls, eid, items=[]):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'image': lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url'])
        }

        result = {
            'eid': eid
        }
        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING and (not len(items) or key in items):
                result.update({key: PROP_MAPPING[key](eid, propid)})

        return result

    @classmethod
    def delete_wide_object(cls, eid):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'image': lambda _eid, _id: PropMedia.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)
