import datetime
import time
import requests
import json
import falcon

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityUser import EntityUser

from each.db import DBConnection
from each.utils import isAllInData

Base = declarative_base()


class EntityToken(EntityBase, Base):
    __tablename__ = 'each_token'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    user_id = Column(Integer)
    access_token = Column(String, primary_key=True)
    type = Column(String, primary_key=True)
    created_at = Column(Date)

    json_serialize_items_list = ['eid', 'user_id' 'access_token', 'type', 'created_at']

    fields_each = {'name': 'name', 'email': 'email', 'image': 'image', 'access_type': 'access_type'}
    fields_swagger = {'name': 'name', 'email': 'email', 'image': 'image', 'access_type': 'access_type'}
    fields_vkontakte = {'name': 'first_name', 'image': 'photo_400_orig'}
    fields_google = {'name': 'given_name', 'email': 'email', 'image': 'picture'}

    allowed_types = ['each', 'vkontakte', 'google', 'swagger']
    granted_types = ['each', 'google', 'swagger']
    revoke_types = ['each', 'google', 'swagger']

    def __init__(self, access_token, type, user_id):
        super().__init__()

        self.user_id = user_id
        self.access_token = access_token
        self.type = type
        ts = time.time()
        self.created_at = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    def __getitem__(self, key):
        return self.__dict__[key]

    @classmethod
    def get_info_api(cls, access_token, type, client=None):
        if client is None:
            with open("client_config.json") as client_config_file:
                client_config = json.load(client_config_file)
                client = client_config['clients'][type]

        req_url = client['token_info_url'] + access_token
        r = requests.get(req_url)
        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        data = r.json()
        if type == 'vkontakte':
            data = data['response'][0]
        res_data = {'access_token': access_token}

        info_fields = cls.__dict__['fields_%s' % type]
        for _ in EntityUser.required_fields:
            if _ in info_fields and info_fields[_] in data:
                res_data[_] = data[info_fields[_]]

        return res_data, falcon.HTTP_200

    @classmethod
    def add_from_query(cls, data):
        if isAllInData(['type', 'redirect_uri', 'code'], data) and data['type'] in cls.allowed_types:
            type = data['type']
            redirect_uri = data['redirect_uri']
            code = data['code']

            with open("client_config.json") as client_config_file:
                client_config = json.load(client_config_file)
                client = client_config['clients'][type]

            request_data = {'client_id': client['client_id'], 'client_secret': client['client_secret'], 'code': code,
                            'redirect_uri': redirect_uri}
            if type in cls.granted_types:
                request_data['grant_type'] = 'authorization_code'

            r = requests.post(client['access_token_url'], data=request_data)
            if r.status_code != 200:
                return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

            res_data, res_status = cls.get_info_api(r.json()['access_token'], type, client)
            if res_status != falcon.HTTP_200:
                return res_data, res_status

            if type == 'vkontakte':
                email = r.json()['email']
            else:
                email = res_data['email']

            user = EntityUser.get().filter_by(email=email, type=type).first()
            if user:
                user_id = user.eid
            else:
                user = EntityUser(type=type, email=email)
                for _ in EntityUser.required_fields:
                    if _ in res_data:
                        user[_] = res_data[_]
                user_id = user.add()

            new_entity = EntityToken(res_data['access_token'], type, user_id)
            eid = new_entity.add()

            return eid, falcon.HTTP_200
        return {'error': 'Invalid parameters supplied'}, falcon.HTTP_400

    @classmethod
    def update_from_query(cls, data):
        if isAllInData(['type', 'access_token'], data) and data['type'] in cls.allowed_types:
            type = data['type']
            access_token = data['access_token']

            token = EntityToken.get().filter_by(access_token=access_token, type=type).first()
            if token:
                user = EntityUser.get().filter_by(eid=token.user_id).first()
                if user:

                    res_data, res_status = cls.get_info_api(access_token, type)
                    if res_status != falcon.HTTP_200:
                        with DBConnection() as session:
                            session.db.delete(token)
                            session.db.commit()
                        return res_data, res_status

                    EntityUser.update_user(token.user_id, res_data)
                    eid = token.eid

                    return eid, falcon.HTTP_200
            return {'error': 'Invalid access token supplied'}, falcon.HTTP_400
        return {'error': 'Invalid parameters supplied'}, falcon.HTTP_400

    @classmethod
    def delete_from_json(cls, data):
        if isAllInData(['type', 'access_token'], data) and data['type'] in cls.allowed_types:
            access_token = data['access_token']
            type = data['type']

            with DBConnection() as session:
                token = session.db.query(EntityToken).filter_by(access_token=access_token, type=type).first()
                if token:
                    if type in cls.revoke_types:
                        with open("client_config.json") as client_config_file:
                            client_config = json.load(client_config_file)
                            client = client_config['clients'][type]
                        requests.post(client['revoke_token_url'], params={'token': access_token},
                                      headers={'content-type': 'application/x-www-form-urlencoded'})

                    session.db.delete(token)
                    session.db.commit()

                    return {'token': access_token}, falcon.HTTP_200
                return {'error': 'Invalid access token supplied'}, falcon.HTTP_400
        return {'error': 'Invalid parameters supplied'}, falcon.HTTP_400
