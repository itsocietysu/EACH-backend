from collections import OrderedDict
import time
import datetime

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityProp import EntityProp

from each.Prop.PropBase import PropBase
from each.Prop.PropMedia import PropMedia

from each.db import DBConnection

Base = declarative_base()

class EntityGame(EntityBase, Base):
    __tablename__ = 'each_game'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    ownerid = Column(String)
    name = Column(String)
    game = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'ownerid', 'name', 'game', 'created', 'updated']

    def __init__(self, ownerid, name, game):
        super().__init__()

        self.ownerid = ownerid
        self.name = name
        self.game = game

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_from_json(cls, data):
        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None
        from each.Prop.PropGame import PropGame

        PROP_MAPPING = {
            'avatar':
                lambda s, _eid, _id, _val, _uid: cls.process_media(s, 'image', _uid, _eid, _id, _val),
            # in table - eid is museum id, and value is eid of game in each_game table
            'game':
                 lambda session, _eid, _id, _value, _uid: PropGame(_value, _id, _eid).add(session=session, no_commit=True)

        }

        if 'ownerid' in data and 'name' in data and 'game' in data and 'prop' in data:
            ownerid = data['ownerid']
            name = data['name']
            game = data['game']

            new_entity = EntityGame(ownerid, name, game)
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
           # 'game': lambda s, _eid, _id, _val: PropGame(eid, _id, _val).add_or_update(session=s, no_commit=True),
            'avatar': lambda s, _eid, _id, _val: PropMedia(eid, _id,
                                                            cls.convert_media_value_to_media_item('image', _eid, _val))
                                                                        .add_or_update(session=s, no_commit=True)
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityGame).filter_by(eid=eid).all()

                if len(entity):
                    for _ in entity:
                        if 'name' in data:
                            _.name = data['name']

                        if 'game' in data:
                            _.description = data['game']

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
           # 'game': lambda _eid, _id: PropGame.get_object_property(_eid, _id),
            'avatar': lambda _eid, _id: PropMedia.get_object_property(_eid, _id, ['eid', 'url'])
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
           # 'game': lambda _eid, _id: PropGame.delete(_eid, _id),
            'avatar': lambda _eid, _id: PropMedia.delete(_eid, _id, False)
        }

        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING:
                PROP_MAPPING[key](eid, propid)