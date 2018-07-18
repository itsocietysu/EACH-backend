from collections import OrderedDict
import time
import datetime

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp
from each.Entities.EntityMuseum import EntityMuseum

from each.Prop.PropBool import PropBool
from each.Prop.PropMedia import PropMedia

from each.db import DBConnection

Base = declarative_base()

class EntityUser(EntityBase, Base):
    __tablename__ = 'each_user'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    login = Column(String)
    e_mail = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'login', 'e_mail', 'created', 'updated']

    def __init__(self, username, email):
        super().__init__()

        self.login = username
        self.e_mail = email

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'private':
                lambda session, _eid, _id, _value, _uid: PropBool(_eid, _id, _value).add(session=session, no_commit=True),
            'avatar':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'image', _uid, _eid, _id, _val)
        }

        if 'username' in data and 'e_mail' in data and 'prop' in data:
            username = data['username']
            e_mail = data['e_mail']

            new_entity = EntityUser(username, e_mail)
            eid = new_entity.add()

            try:
                with DBConnection() as session:
                    for prop_name, prop_val in data['prop'].items():
                        if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                            PROP_MAPPING[prop_name](session, eid, PROPNAME_MAPPING[prop_name], prop_val, eid)
                        else:
                            EntityUser.delete(eid)
                            raise Exception('{%s} not existed property\nPlease use one of:\n%s' %
                                            (prop_name, str(PROPNAME_MAPPING)))

                    session.db.commit()
            except Exception as e:
                EntityUser.delete(eid)
                raise Exception('Internal error')

        return eid

    @classmethod
    def update_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        PROP_MAPPING = {
            'private': lambda s, _eid, _id, _val: PropBool(eid, _id, _val).add_or_update(session=s, no_commit=True),
            'avatar':  lambda s, _eid, _id, _val: PropMedia(eid, _id,
                                                            cls.convert_media_value_to_media_item('image', _eid, _val))
                                                                        .add_or_update(session=s, no_commit=True),
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityUser).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'username' in data:
                            _.username = data['username']

                        if 'e_mail' in data:
                            _.e_mail = data['e_mail']

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
            'private': lambda _eid, _id: PropBool.get_object_property(_eid, _id),
            'avatar': lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url'])
        }

        result = {
            'eid': eid,
            'museum': []
        }
        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING and (not len(items) or key in items):
                result.update({key: PROP_MAPPING[key](eid, propid)})

        museums = EntityMuseum.get().filter_by(ownerid=eid).all()

        for _ in museums:
            result['museum'].append(EntityMuseum.get_wide_object(_.eid))

        return result

    @classmethod
    def delete_wide_object(cls, eid):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'private': lambda _eid, _id: PropBool.delete(_eid, _id, False),
            'avatar': lambda _eid, _id: PropMedia.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)

    @classmethod
    def get_id_from_username(cls, username):
        try:
            return cls.get().filter_by(username=username).all()[0].eid
        except:
            return None

    @classmethod
    def get_id_from_email(cls, e_mail):
        try:
            return cls.get().filter_by(e_mail=e_mail).all()[0].eid
        except:
            return None

    @classmethod
    def is_private(cls, id):
        PROPNAME_MAPPING = EntityProp.map_name_id()
        res = PropBool.get_object_property(id, PROPNAME_MAPPING['private'])
        return res[0] if len(res) else False