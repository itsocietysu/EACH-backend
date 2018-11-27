from collections import OrderedDict
import time
import datetime
import json

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityMedia import EntityMedia
from each.Entities.EntityProp import EntityProp

from each.Prop.PropMedia import PropMedia

from each.db import DBConnection
from each.utils import obj_to_json, isAllInData, image_similarity

Base = declarative_base()


class EntityScenario(EntityBase, Base):
    __tablename__ = 'each_scenario'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    json = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'json', 'created', 'updated']

    def __init__(self, scenario):
        super().__init__()

        self.json = scenario

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def add_by_game_id(cls, game_id):
        eid = None

        if game_id is not None:
            new_entity = EntityScenario('')
            eid = new_entity.add()

            scenario = {'game_id': game_id, 'scenario_id': eid, 'difficulty_bounty': 0,
                        'final_bonus': {'type': 'NONE', 'uri': 'none', 'eid': 0}, 'step_count': 0, 'steps': []}

            with DBConnection() as session:
                entity = session.db.query(EntityScenario).filter_by(eid=eid).first()
                setattr(entity, 'json', obj_to_json(scenario))
                session.db.commit()

        return eid

    @classmethod
    def update_from_json(cls, data):
        def process_image(s, _eid, _id, _val):
            if 'delete' in _val:
                for _ in _val['delete']:
                    PropMedia.delete_by_value(_eid, _id, _)
            images = []
            if 'add' in _val:
                for _ in _val['add']:
                    image_id = cls.convert_media_value_to_media_item('image', _eid, _)
                    uri = '%s%s' % (EntityBase.host, EntityMedia.get().filter_by(eid=image_id).first().url[1:])
                    image = {'eid': image_id, 'uri': uri}
                    images.append(image)
                    PropMedia(eid, _id, image_id).add(session=s, no_commit=True)
            return images

        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None
        props = {}

        PROP_MAPPING = {
            'image': process_image
        }

        if 'id' in data:
            with DBConnection() as session:
                eid = data['id']
                entity = session.db.query(EntityScenario).filter_by(eid=eid).all()
                if len(entity):
                    for _ in entity:
                        if 'json' in data:
                            _.json = data['json']

                        session.db.commit()

                        if 'prop' in data:
                            for prop_name, prop_val in data['prop'].items():
                                if prop_name in PROPNAME_MAPPING and prop_name in PROP_MAPPING:
                                    props[prop_name] = PROP_MAPPING[prop_name](session, eid,
                                                                               PROPNAME_MAPPING[prop_name], prop_val)

                            session.db.commit()

                        ts = time.time()
                        _.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                        session.db.commit()

        return eid, props

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

    @classmethod
    def delete(cls, eid):
        with DBConnection() as session:
            res = session.db.query(cls).filter_by(eid=eid).all()

            if len(res):
                [[cls.delete_wide_object(eid), session.db.delete(_)] for _ in res]
                session.db.commit()
            else:
                raise FileNotFoundError('%s was not found' % cls.__name__)

    @classmethod
    def check_similar_image(cls, data):

        similar = False

        if isAllInData(['id', 'stepid', 'image'], data):
            with DBConnection() as session:
                eid = data['id']
                stepid = data['stepid']
                base = data['image']
                entity = session.db.query(EntityScenario).filter_by(eid=eid).all()
                if len(entity):
                    for _ in entity:
                        scenario = json.loads(_.json)
                        if 0 <= int(stepid) < scenario['step_count']:
                            step = scenario['steps'][stepid]
                            if step['type'] == 'ar_paint_question':
                                image_path = '.%s' % step['desc']['target']['uri']["http://each.itsociety.su:4201/each"
                                                                                   .__len__():]

                                similar = image_similarity(base, image_path)

        return similar
