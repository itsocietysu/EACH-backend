from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class PropGame(PropBase, Base):
    __tablename__ = 'each_prop_game'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)
