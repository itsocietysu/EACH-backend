from each.Prop.PropBase import PropBase

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class PropInt(PropBase, Base):
    __tablename__ = 'each_prop_int'

    def __init__(self, eid, propid, value):
        super().__init__(eid, propid, value)
