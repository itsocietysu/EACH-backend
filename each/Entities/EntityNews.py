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
from each.Prop.PropInt import PropInt

from each.db import DBConnection
from each.utils import isAllInData

Base = declarative_base()


class EntityNews(EntityBase, Base):
    __tablename__ = 'each_news'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    title_RU = Column(String)
    title_EN = Column(String)
    desc_RU = Column(String)
    desc_EN = Column(String)
    text_EN = Column(String)
    text_RU = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'title_RU', 'title_EN', 'desc_RU', 'desc_EN',
                                 'text_RU', 'text_EN', 'created', 'updated']
    locales = ['RU', 'EN']

    def __init__(self, title_RU, title_EN, desc_RU, desc_EN, text_RU, text_EN):
        super().__init__()

        self.title_RU = title_RU
        self.title_EN = title_EN

        self.desc_RU = desc_RU
        self.desc_EN = desc_EN

        self.text_RU = text_RU
        self.text_EN = text_EN

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data):
        eid = None

        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'image':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'image', _uid, _eid, _id, _val),
            'priority':
                lambda s, _eid, _id, _val, _uid: PropInt(eid, _id, _val).add_or_update(session=s, no_commit=False)
        }
        if isAllInData(['title', 'desc', 'text', 'prop'], data):
            create_args = {}
            if 'prop' in data:
                for _ in cls.locales:
                    create_args['title_%s' % _] = data['title'][_] if _ in data['title'] else ''
                    create_args['desc_%s' % _] = data['desc'][_] if _ in data['desc'] else ''
                    create_args['text_%s' % _] = data['text'][_] if _ in data['text'] else ''
            new_entity = EntityNews(**create_args)

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
                lambda s, _eid, _id, _val: [PropMedia.delete(_eid, _id), PropMedia(_eid, _id,
                                                           cls.convert_media_value_to_media_item('image', _eid, _val))
                                                                    .add_or_update(session=s, no_commit=True)],
            'priority':
                lambda s, _eid, _id, _val: PropInt(eid, _id, _val).add_or_update(session=s, no_commit=True)
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityNews).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'RU' in data['title']:
                            _.title_RU = data['title']['RU']
                        if 'EN' in data['title']:
                            _.title_EN = data['title']['EN']
                        if 'RU' in data['desc']:
                            _.title_RU = data['desc']['RU']
                        if 'EN' in data['desc']:
                            _.title_EN = data['desc']['EN']
                        if 'RU' in data['text']:
                            _.text_RU = data['text']['RU']
                        if 'EN' in data['text']:
                            _.title_EN = data['text']['EN']
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
            'image':
                lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url']),
            'priority':
                lambda _eid, _id: [_.value for _ in PropInt.get().filter_by(eid=_eid, propid=_id).all() or [PropInt(0, 0, 0)]]
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
            'image':
                lambda _eid, _id: PropMedia.delete(_eid, _id, False),
            'priority':
                lambda _eid, _id: PropInt.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)
