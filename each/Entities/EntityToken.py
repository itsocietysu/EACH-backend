import datetime
import time
import requests
import json
import falcon

from sqlalchemy import Column, String, Integer, Date, Sequence
from sqlalchemy.ext.declarative import declarative_base

from each.Entities.EntityBase import EntityBase

from each.db import DBConnection
from each.utils import isAllInData

Base = declarative_base()


class EntityToken(EntityBase, Base):
    __tablename__ = 'each_user'

    eid = Column(Integer, Sequence('each_seq'), primary_key=True)
    access_token = Column(String, primary_key=True)
    type = Column(String, primary_key=True)
    login = Column(String)
    email = Column(String)
    image = Column(String)
    access_type = Column(String)
    created = Column(Date)
    updated = Column(Date)

    json_serialize_items_list = ['eid', 'access_token', 'type', 'login', 'email', 'image',
                                 'access_type', 'created', 'updated']

    def __init__(self, access_token, type, login, email, image, access_type):
        super().__init__()

        self.access_token = access_token
        self.type = type

        self.login = login
        self.email = email
        self.image = image
        self.access_type = access_type

        ts = time.time()
        self.created = self.updated = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def get_info_each(cls, access_token):
        req_url = 'http://each.itsociety.su:5000/oauth2/tokeninfo?access_token=%s' % access_token
        r = requests.get(req_url)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        data = r.json()

        res_data = {'access_token': access_token}

        if 'name' in data:
            res_data['login'] = data['name']
        if 'email' in data:
            res_data['email'] = data['email']
        if 'access_type' in data:
            res_data['access_type'] = data['access_type']
        if 'image' in data:
            res_data['image'] = data['image']

        return res_data, falcon.HTTP_200

    @classmethod
    def get_info_vkontakte(cls, access_token):
        req_url = 'https://api.vk.com/method/users.get?fields=photo_200_orig&access_token=%s&v=5.85' % access_token
        r = requests.get(req_url)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        data = r.json()['response'][0]

        res_data = {'access_token': access_token}

        if 'first_name' in data:
            res_data['login'] = data['first_name']
        if 'photo_200_orig' in data:
            res_data['image'] = data['photo_200_orig']

        return res_data, falcon.HTTP_200

    @classmethod
    def get_info_google(cls, access_token):
        req_url = 'https://www.googleapis.com/oauth2/v2/userinfo?access_token=%s' % access_token
        r = requests.get(req_url)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        data = r.json()

        res_data = {'access_token': access_token}

        if 'given_name' in data:
            res_data['login'] = data['given_name']
        if 'email' in data:
            res_data['email'] = data['email']
        if 'picture' in data:
            res_data['image'] = data['picture']

        return res_data, falcon.HTTP_200

    @classmethod
    def get_token_each(cls, data):
        redirect_uri = data['redirect_uri']
        code = data['code']

        with open("client_config.json") as client_config_file:
            client_config = json.load(client_config_file)

        client = client_config['clients']['each']
        request_data = {'client_id': client['client_id'], 'client_secret': client['client_secret'], 'code': code,
                        'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}

        r = requests.post(client['access_token_url'], data=request_data)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        res_data, res_status = cls.get_info_each(r.json()['access_token'])

        if res_status != falcon.HTTP_200:
            return res_data, res_status

        access_token = res_data['access_token']
        email = res_data['email']
        login = res_data['login']
        access_type = res_data['access_type']
        image = res_data['image']

        new_entity = EntityToken(access_token, 'each', login, email, image, access_type)
        eid = new_entity.add()

        with DBConnection() as session:
            session.db.commit()

        return eid, falcon.HTTP_200

    @classmethod
    def get_token_vkontakte(cls, data):
        redirect_uri = data['redirect_uri']
        code = data['code']

        with open("client_config.json") as client_config_file:
            client_config = json.load(client_config_file)

        client = client_config['clients']['vkontakte']
        request_data = {'client_id': client['client_id'], 'client_secret': client['client_secret'], 'code': code,
                        'redirect_uri': redirect_uri}

        r = requests.post(client['access_token_url'], data=request_data)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        email = r.json()['email']
        res_data, res_status = cls.get_info_vkontakte(r.json()['access_token'])

        if res_status != falcon.HTTP_200:
            return res_data, res_status

        access_token = res_data['access_token']
        login = res_data['login']
        image = res_data['image']

        new_entity = EntityToken(access_token, 'vkontakte', login, email, image, 'user')
        eid = new_entity.add()

        with DBConnection() as session:
            session.db.commit()

        return eid, falcon.HTTP_200

    @classmethod
    def get_token_google(cls, data):
        redirect_uri = data['redirect_uri']
        code = data['code']

        with open("client_config.json") as client_config_file:
            client_config = json.load(client_config_file)

        client = client_config['clients']['google']
        request_data = {'client_id': client['client_id'], 'client_secret': client['client_secret'], 'code': code,
                        'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}

        r = requests.post(client['access_token_url'], data=request_data)

        if r.status_code != 200:
            return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

        res_data, res_status = cls.get_info_google(r.json()['access_token'])

        if res_status != falcon.HTTP_200:
            return res_data, res_status

        access_token = res_data['access_token']
        login = res_data['login']
        email = res_data['email']
        image = res_data['image']

        new_entity = EntityToken(access_token, 'google', login, email, image, 'user')
        eid = new_entity.add()

        with DBConnection() as session:
            session.db.commit()

        return eid, falcon.HTTP_200

    @classmethod
    def add_from_query(cls, data):
        return cls.__dict__['get_token_%s' % data['client_name']].__get__(None, cls)(data)

    @classmethod
    def get_tokeninfo_each(cls, data):
        access_token = data['access_token']

        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='each').first()

            if token:
                res_data, res_status = cls.get_info_each(access_token)

                if res_status != falcon.HTTP_200:
                    return res_data, res_status

                token.email = res_data['email']
                token.login = res_data['login']
                token.access_type = res_data['access_type']
                eid = token.eid

                session.db.commit()

                return eid, falcon.HTTP_200

        return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def get_tokeninfo_vkontakte(cls, data):
        access_token = data['access_token']

        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='vkontakte').first()

            if token:
                res_data, res_status = cls.get_info_vkontakte(access_token)

                if res_status != falcon.HTTP_200:
                    return res_data, res_status

                token.image = res_data['image']
                token.login = res_data['login']
                eid = token.eid

                session.db.commit()

                return eid, falcon.HTTP_200

        return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def get_tokeninfo_google(cls, data):
        access_token = data['access_token']

        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='google').first()

            if token:
                res_data, res_status = cls.get_info_google(access_token)

                if res_status != falcon.HTTP_200:
                    return res_data, res_status

                token.image = res_data['image']
                token.login = res_data['login']
                eid = token.eid

                session.db.commit()

                return eid, falcon.HTTP_200

        return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def update_from_query(cls, data):
        return cls.__dict__['get_tokeninfo_%s' % data['client_name']].__get__(None, cls)(data)

    @classmethod
    def revoke_token_each(cls, access_token):
        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='each').first()
            if token:
                r = requests.post('http://each.itsociety.su:5000/oauth2/revoke_bearer',
                                  data={'access_token': access_token})

                if r.status_code != 200:
                    return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

                session.db.delete(token)
                session.db.commit()
                return {'token': access_token}, falcon.HTTP_200

            return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def revoke_token_vkontakte(cls, access_token):
        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='vkontakte').first()
            if token:
                session.db.delete(token)
                session.db.commit()
                return {'token': access_token}, falcon.HTTP_200

            return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def revoke_token_google(cls, access_token):
        with DBConnection() as session:
            token = session.db.query(EntityToken).filter_by(access_token=access_token, type='google').first()
            if token:
                r = requests.post('https://accounts.google.com/o/oauth2/revoke', params={'token': access_token},
                                  headers={'content-type': 'application/x-www-form-urlencoded'})

                if r.status_code != 200 and r.json()['error'] != 'invalid_token':
                    return r.json(), falcon.__dict__['HTTP_%s' % r.status_code]

                session.db.delete(token)
                session.db.commit()
                return {'token': access_token}, falcon.HTTP_200

            return {'error': 'Invalid access token supplied'}, falcon.HTTP_400

    @classmethod
    def delete_from_json(cls, data):
        if isAllInData(['type', 'access_token'], data):
            return cls.__dict__['revoke_token_%s' % data['type']].__get__(None, cls)(data['access_token'])
        return {'error': 'invalid arguments'}, falcon.HTTP_400
