import datetime
import json
import time
from collections import OrderedDict

from sqlalchemy import Column, String, Integer, Sequence, Interval, Date
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityProp import EntityProp
from each.Entities.EntityScenario import EntityScenario
from each.Entities.EntityBase import EntityBase
from each.Prop.PropInterval import PropInterval
from each.Prop.PropScenario import PropScenario
from each.db import DBConnection
from each.utils import isAllInData, _interval_to_string

Base = declarative_base()


class EntityRun(EntityBase, Base):
    __tablename__ = 'each_run'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    step_passed = Column(Integer)
    status = Column(String)
    game_id = Column(Integer)
    start_time = Column(Date)
    best_time = Column(Interval)
    bonus = Column(Integer)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'step_passed', 'status', 'game_id', 'start_time', 'best_time', 'bonus']

    def __init__(self, game_id):
        super().__init__()

        self.step_passed = 0
        self.status = 'process'
        self.game_id = game_id
        self.best_time = datetime.timedelta(seconds=0)
        self.bonus = 0

        ts = time.time()
        self.start_time = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    def to_dict(self, items=[]):
        def get_value(key):
            if key == 'best_time':
                return _interval_to_string(self.best_time)
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

        res = OrderedDict([(key, get_value(key))
                           for key in (self.json_serialize_items_list if not len(items) else items)])
        return res

    @classmethod
    def update_from_json(cls, data):
        from each.Prop.PropRun import PropRun

        def create_new_entity():
            new_entity = EntityRun(game)
            n_eid = new_entity.add()
            PropRun(user, PROPNAME_MAPPING['run'], n_eid).add()
            return [n_eid]

        PROPNAME_MAPPING = EntityProp.map_name_id()

        eid = None

        if isAllInData(['user_id', 'game_id', 'step_passed'], data):

            user = data['user_id']
            game = data['game_id']
            steps = data['step_passed']

            prop_scenario = PropScenario.get().filter_by(eid=game, propid=PROPNAME_MAPPING['scenario']).all()
            if len(prop_scenario):
                with DBConnection() as session:
                    entity = [_[1] for _ in session.db.query(PropRun, EntityRun).filter(PropRun.eid == user).
                              filter(PropRun.value == EntityRun.eid).filter(EntityRun.game_id == game).all()]
                    if not len(entity):
                        _eid = create_new_entity()
                        entity = session.db.query(EntityRun).filter_by(eid=_eid)
                    times = session.db.query(PropInterval).filter_by(eid=user).all()
                    if not len(times):
                        PropInterval(user, PROPNAME_MAPPING['time_in_game'], datetime.timedelta(seconds=0)).\
                            add(session=session)
                        times = session.db.query(PropInterval).filter_by(eid=user).all()
                    for ps in prop_scenario:
                        scenario = EntityScenario.get().filter_by(eid=ps.value).all()
                        if len(scenario):
                            for s in scenario:
                                sc = json.loads(s.json)
                                for _ in entity:
                                    eid = _.eid
                                    _.step_passed = steps
                                    ts = time.time()
                                    if steps == 0:
                                        _.start_time = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                                    if sc['step_count'] == steps:
                                        _.status = 'pass'
                                        if _.bonus == 0:
                                            _.bonus = int(sc['difficulty_bounty'])
                                        d_time = datetime.datetime.fromtimestamp(ts) - \
                                            datetime.datetime.strptime(_.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                                       '%Y-%m-%d %H:%M:%S')
                                        if _.best_time == 0 or _.best_time > d_time:
                                            one_week = datetime.timedelta(weeks=1)
                                            if d_time > one_week:
                                                _.best_time = one_week
                                            else:
                                                _.best_time = d_time
                                        for t in times:
                                            t.value += d_time
                                    else:
                                        _.status = 'process'
                                    _.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                                    session.db.commit()

        return eid
