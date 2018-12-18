import datetime
import time

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityGame import EntityGame
from each.Entities.EntityProp import EntityProp
from each.Prop.PropInterval import PropInterval
from each.Prop.PropRun import PropRun

from each.db import DBConnection

Base = declarative_base()


class EntityUser(EntityBase, Base):
    __tablename__ = 'each_user'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    type = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, primary_key=True)
    image = Column(String)
    access_type = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'type', 'name', 'email', 'image',
                                 'access_type', 'created', 'updated']
    required_fields = ['name', 'email', 'image', 'access_type']

    def __init__(self, type='each', name='user', email=None, image=None, access_type='user'):
        super().__init__()

        self.type = type
        self.name = name
        self.email = email
        self.image = image
        self.access_type = access_type

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]

    @classmethod
    def update_user(cls, eid, data):

        with DBConnection() as session:
            entity = session.db.query(EntityUser).filter_by(eid=eid).first()
            if entity:
                for _ in cls.required_fields:
                    if _ in data:
                        setattr(entity, _, data[_])

                ts = time.time()
                entity.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                session.db.commit()

    @classmethod
    def get_wide_object(cls, eid, items=[]):
        def get_run(_eid, _id):
            objects = PropRun.get_object_property(_eid, _id)
            passed = []
            process = []
            bonus = 0
            for o in objects:
                games = EntityGame.get().filter_by(eid=int(o['game_id'])).all()
                if len(games):
                    for g in games:
                        obj_dict = g.to_dict(['eid', 'ownerid', 'name', 'desc'])
                        wide_info = EntityGame.get_wide_object(g.eid, ['image', 'scenario'])
                        obj_dict.update(wide_info)
                        if o['best_time'] != '0':
                            obj_dict.update({'best_time': o['best_time']})
                            passed.append(obj_dict)
                            bonus += int(o['bonus'])
                        if o['status'] == 'process':
                            obj_dict.update({'step_passed': o['step_passed']})
                            process.append(obj_dict)
            return {'game_passed': passed, 'game_process': process, 'bonus': bonus}

        def get_time_in_game(_eid, _id):
            times = PropInterval.get_object_property(eid, _id)
            if not len(times):
                return "0s"
            return times[0]

        PROPNAME_MAPPING = EntityProp.map_name_id()

        PROP_MAPPING = {
            'run': get_run,
            'time_in_game': get_time_in_game
        }

        result = {}
        for key, propid in PROPNAME_MAPPING.items():
            if key in PROP_MAPPING and (not len(items) or key in items):
                result.update({key: PROP_MAPPING[key](eid, propid)})

        return result
