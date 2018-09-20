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

    def __init__(self, access_token, type, user_id):
        super().__init__()

        self.user_id = user_id
        self.access_token = access_token
        self.type = type
        ts = time.time()
        self.created_at = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

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

        with DBConnection() as session:
            user = session.db.query(EntityUser).filter_by(email=email, type='each').first()
            if user:
                user_id = user.eid
            else:
                user_id = EntityUser('each', login, email, image, access_type).add()

            new_entity = EntityToken(access_token, 'each', user_id)
            eid = new_entity.add()

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

        with DBConnection() as session:
            user = session.db.query(EntityUser).filter_by(email=email, type='vkontakte').first()
            if user:
                user_id = user.eid
            else:
                user_id = EntityUser('vkontakte', login, email, image, 'user').add()

            new_entity = EntityToken(access_token, 'vkontakte', user_id)
            eid = new_entity.add()

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

        with DBConnection() as session:
            user = session.db.query(EntityUser).filter_by(email=email, type='google').first()
            if user:
                user_id = user.eid
            else:
                user_id = EntityUser('google', login, email, image, 'user').add()

            new_entity = EntityToken(access_token, 'google', user_id)
            eid = new_entity.add()

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
                user = session.db.query(EntityUser).filter_by(eid=token.user_id).first()

                if user:
                    res_data, res_status = cls.get_info_each(access_token)

                    if res_status != falcon.HTTP_200:
                        return res_data, res_status

                    user.email = res_data['email']
                    user.login = res_data['login']
                    user.access_type = res_data['access_type']
                    user.image = res_data['image']
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
                user = session.db.query(EntityUser).filter_by(eid=token.user_id).first()

                if user:
                    res_data, res_status = cls.get_info_vkontakte(access_token)

                    if res_status != falcon.HTTP_200:
                        return res_data, res_status

                    user.image = res_data['image']
                    user.login = res_data['login']
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
                user = session.db.query(EntityUser).filter_by(eid=token.user_id).first()

                if user:
                    res_data, res_status = cls.get_info_google(access_token)

                    if res_status != falcon.HTTP_200:
                        return res_data, res_status

                    user.image = res_data['image']
                    user.login = res_data['login']
                    user.email = res_data['email']
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
