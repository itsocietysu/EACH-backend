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

Base = declarative_base()

class EntityMuseum(EntityBase, Base):
    __tablename__ = 'each_museum'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    ownerid = Column(Integer)
    name = Column(String)
    desc = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'ownerid', 'name', 'desc', 'created', 'updated']

    def __init__(self, ownerid, name, desc):
        super().__init__()

        self.ownerid = ownerid
        self.name = name
        self.desc = desc

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'private':
                lambda session, _eid, _id, _value, _uid: PropBool(_eid, _id, _value)
                    .add(session=session, no_commit=True),
            'isopen':
                lambda session, _eid, _id, _value, _uid: PropBool(_eid, _id, _value)
                    .add(session=session, no_commit=True),
            'isfree':
                lambda session, _eid, _id, _value, _uid: PropBool(_eid, _id, _value)
                    .add(session=session, no_commit=True),
            'isonair':
                lambda session, _eid, _id, _value, _uid: PropBool(_eid, _id, _value)
                    .add(session=session, no_commit=True),
            'price':
                lambda session, _eid, _id, _value, _uid: PropReal(_eid, _id, _value)
                    .add(session=session, no_commit=True),
            'location':
                lambda s, _eid, _id, _val, _uid: PropLocation(_eid, _id, _val)
                    .add(session=s, no_commit=True),
            'media':
                lambda s, _eid, _id, _val, _uid: [cls.process_media(s, 'image', _uid, _eid, _id, _)
                                                    for _ in _val],
            'equipment':
                lambda s, _eid, _id, _val, _uid: [cls.process_media(s, 'equipment', _uid, _eid, _id, _)
                                                    for _ in _val]
        }

        if 'ownerid' in data and 'name' in data and 'desc' in data and 'prop' in data:
            ownerid = data['ownerid']
            name = data['name']
            desc = data['desc']

            new_entity = EntityMuseum(ownerid, name, desc)
            eid = new_entity.add()

            with DBConnection() as session:
                for prop_name, prop_val in data['prop'].items():
                    if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                        PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val, ownerid)
                    else:
                        new_entity.delete(eid)
                        raise Exception('{%s} not existed property\nPlease use one of:\n%s' %
                                        (prop_name, str(PROPNAME_MAPPING)))

                session.db.commit()

        return eid

    @classmethod
    def __update_equipment(cls, s, _eid, _id, _val, _uid):
        if 'del' in _val:
            PropMedia.deleteList(_eid, _id, _val['del'], s, False)

        if 'new' in _val:
            for _val_new in _val['new']:
                cls.process_media(s, 'equipment', _uid, _eid, _id, _val_new)



    @classmethod
    def update_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'location':
                lambda s, _eid, _id, _val, _uid:
                PropLocation(_eid, _id, _val).update(session=s)
                if len(PropLocation.get().filter_by(eid=_eid, propid=_id).all())
                else PropLocation(_eid, _id, _val).add(session=s),
            'equipment':
                lambda s, _eid, _id, _val, _uid: cls.__update_equipment(s,_eid, _id, _val, _uid),
            'description':
                lambda s, _eid, _id, _val, _uid:
                PropComment(_eid, _id, _val).update(session=s)
                if len(PropComment.get().filter_by(eid=_eid, propid=_id).all())
                else PropComment(_eid, _id, _val).add(session=s),
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                ownerid = data['ownerid']
                entity = session.db.query(EntityMuseum).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'username' in data:
                            _.username = data['username']

                        if 'e_mail' in data:
                            _.e_mail = data['e_mail']

                        session.db.commit()

                        for prop_name, prop_val in data['prop'].items():
                            if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                                PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val, ownerid)

                        session.db.commit()

        return eid

    @classmethod
    def get_wide_object(cls, eid, items=[]):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'private':   lambda _eid, _id: PropBool.get_object_property(_eid, _id),
            'isopen':    lambda _eid, _id: PropBool.get_object_property(_eid, _id),
            'isfree':    lambda _eid, _id: PropBool.get_object_property(_eid, _id),
            'isonair':   lambda _eid, _id: PropBool.get_object_property(_eid, _id),
            'price':     lambda _eid, _id: PropReal.get_object_property(_eid, _id),
            'location':  lambda _eid, _id: PropLocation.get_object_property(_eid, _id),
            'media':     lambda _eid, _id: PropMedia.get_object_property(_eid, _id),
            'equipment': lambda _eid, _id: PropMedia.get_object_property(_eid, _id)
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
            'private':   lambda _eid, _id: PropBool.delete(_eid, _id, False),
            'isopen':    lambda _eid, _id: PropBool.delete(_eid, _id, False),
            'isfree':    lambda _eid, _id: PropBool.delete(_eid, _id, False),
            'isonair':   lambda _eid, _id: PropBool.delete(_eid, _id, False),
            'price':     lambda _eid, _id: PropReal.delete(_eid, _id, False),
            'location':  lambda _eid, _id: PropLocation.delete(_eid, _id, False),
            'media':     lambda _eid, _id: PropMedia.delete(_eid, _id, False),
            'equipment': lambda _eid, _id: PropMedia.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)