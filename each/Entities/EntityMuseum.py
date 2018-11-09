from collections import OrderedDict
import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp

from each.Prop.PropBool import PropBool
from each.Prop.PropReal import PropReal
from each.Prop.PropMedia import PropMedia
from each.Prop.PropLocation import PropLocation
from each.Prop.PropComment import PropComment
from each.db import DBConnection

from each.Prop.PropGame import PropGame
from each.utils import isAllInData

Base = declarative_base()

class EntityMuseum(EntityBase, Base):
    __tablename__ = 'each_museum'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    ownerid = Column(Integer)
    name_RU = Column(String)
    name_EN = Column(String)
    desc_RU = Column(String)
    desc_EN = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'ownerid', 'name', 'desc', 'created', 'updated']

    def __init__(self, ownerid, name_RU, name_EN, desc_RU, desc_EN):
        super().__init__()

        self.ownerid = ownerid
        self.name_RU = name_RU
        self.name_EN = name_EN
        self.desc_RU = desc_RU
        self.desc_EN = desc_EN

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    def to_dict(self, items=[]):
        def fullfill_entity(key, value):
            if key == 'url':
                value = '%s%s' % (EntityBase.host, value[1:])
            return value

        def get_value(key):
            if key == 'name':
                return self.name
            elif key == 'desc':
                return self.desc
            else:
                return dictionate_entity(self.__dict__[key])

        def dictionate_entity(entity):
            try:
                json.dump(entity)
                return entity
            except:
                if 'to_dict' in dir(entity):
                    return entity.to_dict()
                else:
                    return str(entity)

        res = OrderedDict([(key, fullfill_entity(key, get_value(key)))
                           for key in (self.json_serialize_items_list if not len(items) else items)])
        return res

    @property
    def name(self):
        return {_: self.__dict__['name_%s' % _] for _ in self.locales}

    @property
    def desc(self):
        return {_: self.__dict__['desc_%s' % _] for _ in self.locales}

    @classmethod
    def add_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'logo':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'logo', _uid, _eid, _id, _val),
            'image':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'image', _uid, _eid, _id, _val),
            'location':
                lambda s, _eid, _id, _val, _uid: [PropLocation(_eid, _id, _).add(session=s, no_commit=True)
                                                  for _ in _val['add']]
        }

        if isAllInData(['name', 'desc', 'ownerid', 'prop'], data):
            create_args = {'ownerid': data['ownerid']}
            for _ in cls.locales:
                create_args['name_%s' % _] = data['name'][_] if _ in data['name'] else ''
                create_args['desc_%s' % _] = data['desc'][_] if _ in data['desc'] else ''
            new_entity = EntityMuseum(**create_args)
            eid = new_entity.add()

            with DBConnection() as session:
                for prop_name, prop_val in data['prop'].items():
                    if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                        PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val, eid)
                    else:
                        new_entity.delete(eid)
                        raise Exception('{%s} not existed property\nPlease use one of:\n%s' %
                                        (prop_name, str(PROPNAME_MAPPING)))

                session.db.commit()

        return eid

    @classmethod
    def update_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'logo': lambda s, _eid, _id, _val: [PropMedia.delete(_eid, _id), PropMedia(eid, _id,
                                                            cls.convert_media_value_to_media_item('logo', _eid, _val))
                                                                        .add_or_update(session=s, no_commit=True)],
            'image': lambda s, _eid, _id, _val: [PropMedia.delete(_eid, _id), PropMedia(eid, _id,
                                                            cls.convert_media_value_to_media_item('image', _eid, _val))
                                                                        .add_or_update(session=s, no_commit=True)],
            'location':
                lambda s, _eid, _id, _val: [[PropLocation(_eid, _id, _).add(session=s, no_commit=True)
                                            for _ in _val['add']],
                                            [PropLocation.delete_by_value(_eid, _id, _)
                                            for _ in _val['delete']]]
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityMuseum).filter_by(eid=eid).all()
                fields = ['name', 'desc']
                if len(entity):
                    for _ in entity:
                        for l in cls.locales:
                            for f in fields:
                                if f in data and l in data[f]:
                                    setattr(_, '%s_%s' % (f, l), data[f][l])
                        session.db.commit()

                        if 'prop' in data:
                            for prop_name, prop_val in data['prop'].items():
                                if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                                    PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val)
                        session.db.commit()

        return eid

    @classmethod
    def get_wide_object(cls, eid, items=[]):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'logo': lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url']),
            'image': lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url']),
            'game': lambda _eid, _id: PropGame.get_object_property(_eid, _id, ['eid', 'ownerid', 'name', 'desc']),
            'location': lambda _eid, _id: PropLocation.get_object_property(_eid, _id)
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
            'logo': lambda _eid, _id: PropMedia.delete(_eid, _id, False),
            'image': lambda _eid, _id: PropMedia.delete(_eid, _id, False),
            'location': lambda _eid, _id: PropLocation.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)