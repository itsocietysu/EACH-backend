import concurrent.futures as ftr
import json
import logging
import mimetypes
import os
import posixpath
import re
import time
import math
from urllib.parse import parse_qs
from collections import OrderedDict

import falcon
from falcon_multipart.middleware import MultipartMiddleware

from each import utils
from each.db import DBConnection
from each.serve_swagger import SpecServer
from each.utils import obj_to_json, getIntPathParam, getIntQueryParam, getStringQueryParam, admin_access_type_required

from each.Entities.EntityBase import EntityBase
from each.Entities.EntityMedia import EntityMedia
from each.Entities.EntityNews import EntityNews
from each.Entities.EntityMuseum import EntityMuseum
from each.Entities.EntityGame import EntityGame
from each.Entities.EntityScenario import EntityScenario
from each.Entities.EntityToken import EntityToken
from each.Entities.EntityUser import EntityUser
from each.Entities.EntityLocation import EntityLocation

from each.Prop.PropMedia import PropMedia
from each.Prop.PropInt import PropInt
from each.Prop.PropGame import PropGame

from each.auth import auth


# from each.MediaResolver.MediaResolverFactory import MediaResolverFactory

def guess_response_type(path):
    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types

    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })

    base, ext = posixpath.splitext(path)
    if ext in extensions_map:
        return extensions_map[ext]
    ext = ext.lower()
    if ext in extensions_map:
        return extensions_map[ext]
    else:
        return extensions_map['']


def date_time_string(timestamp=None):
    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        weekdayname[wd],
        day, monthname[month], year,
        hh, mm, ss)
    return s


def httpDefault(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    path = req.path
    src_path = path
    path = path.replace(baseURL, '.')

    if os.path.isdir(path):
        for index in "index.html", "index.htm", "test-search.html":
            index = os.path.join(path + '/', index)
            if os.path.exists(index):
                path = index
                break
        else:
            return None

    if path.endswith('swagger.json'):
        path = path.replace('swagger.json', 'swagger_temp.json')

    ctype = guess_response_type(path)

    try:
        with open(path, 'rb') as f:
            resp.status = falcon.HTTP_200

            fs = os.fstat(f.fileno())
            length = fs[6]

            buffer = f.read()
            if path.endswith('index.html'):
                str = buffer.decode()
                str = str.replace('127.0.0.1:4201', server_host)
                buffer = str.encode()
                length = len(buffer)

    except IOError:
        resp.status = falcon.HTTP_404
        return

    resp.set_header("Content-type", ctype)
    resp.set_header("Content-Length", length)
    resp.set_header("Last-Modified", date_time_string(fs.st_mtime))
    resp.set_header("Access-Control-Allow-Origin", "*")
    resp.set_header("Path", path)
    resp.body = buffer


def getVersion(**request_handler_args):
    resp = request_handler_args['resp']
    resp.status = falcon.HTTP_200
    with open("VERSION") as f:
        resp.body = obj_to_json({"version": f.read()[0:-1]})


def getFeedMockup(**request_handler_args):
    resp = request_handler_args['resp']
    resp.status = falcon.HTTP_200
    with open("feed.json") as f:
        resp.body = f.read()


@admin_access_type_required
def addFeed(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        params['ownerid'] = req.context['user_id']
        id = EntityNews.add_from_json(params)

        if id:
            objects = EntityNews.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'title', 'desc', 'text'])
                wide_info = EntityNews.get_wide_object(_.eid, ['image', 'priority'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


@admin_access_type_required
def updateFeed(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))

        id = EntityNews.update_from_json(params)

        if id:
            objects = EntityNews.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'title', 'desc', 'text'])
                wide_info = EntityNews.get_wide_object(_.eid, ['image', 'priority'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


def getTapeFeeds(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    first_f = getIntQueryParam('FirstFeed', **request_handler_args)
    last_f = getIntQueryParam('LastFeed', **request_handler_args)

    with DBConnection() as session:
        objects = session.db.query(EntityNews, PropInt.value) \
            .join(PropInt, PropInt.eid == EntityNews.eid) \
            .order_by(PropInt.value.desc(), EntityNews.created.desc()).all()

        count = objects.__len__()

    if first_f < 0:
        first_f = 0

    # if last_f isn't set (==-1), it is supposed to be an infinity
    if last_f == -1:
        feeds = objects[first_f:]
    else:
        feeds = objects[first_f: last_f + 1]

    if feeds.__len__() == 0:
        if count > 0:
            if first_f > 0:
                first_f = min(int(first_f - math.fmod(first_f, 10)), int(count - math.fmod(count, 10)))
            elif first_f < 0:
                first_f = 0
            feeds = objects[first_f: first_f + 10]
        else:
            first_f = 0
    page = int((first_f - math.fmod(first_f, 10)) / 10) + 1

    res = []
    for _ in feeds:
        obj_dict = _[0].to_dict(['eid', 'title', 'desc', 'text'])
        wide_info = EntityNews.get_wide_object(_[0].eid, ['image', 'priority'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    res_dict = OrderedDict([('count', count), ('page', page), ('result', res)])

    resp.body = obj_to_json(res_dict)
    resp.status = falcon.HTTP_200


def getAllFeeds(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']
    objects = EntityNews.get().all()
    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'title', 'desc', 'text'])
        wide_info = EntityNews.get_wide_object(_.eid, ['image', 'priority'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    res.sort(key=lambda row: row['priority'], reverse=True)
    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def getFeedById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("feedId", **request_handler_args)
    objects = EntityNews.get().filter_by(eid=id).all()

    wide_info = EntityNews.get_wide_object(id, ['image', 'priority'])

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'title', 'desc', 'text'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


@admin_access_type_required
def deleteFeed(**request_handler_args):
    resp = request_handler_args['resp']
    req = request_handler_args['req']

    id = getIntPathParam("feedId", **request_handler_args)
    res = []
    try:
        EntityNews.delete(id)
    except FileNotFoundError:
        resp.status = falcon.HTTP_404
        return

    try:
        EntityNews.delete_wide_object(id)
    except FileNotFoundError:
        resp.status = falcon.HTTP_405
        return

    object = EntityNews.get().filter_by(eid=id).all()
    if not len(object):
        resp.body = obj_to_json(res)
        resp.status = falcon.HTTP_200
        return

    resp.status = falcon.HTTP_400


# museum feature set functions
# ----------------------------


def getAllMuseumsMockup(**request_handler_args):
    resp = request_handler_args['resp']
    resp.status = falcon.HTTP_200
    with open("museum.json") as f:
        resp.body = f.read()


def getAllMuseums(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    objects = EntityMuseum.get().all()

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
        wide_info = EntityMuseum.get_wide_object(_.eid, ['image', 'game', 'location'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def getTapeMuseums(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    first_m = getIntQueryParam('FirstMuseum', **request_handler_args)
    last_m = getIntQueryParam('LastMuseum', **request_handler_args)

    with DBConnection() as session:
        objects = session.db.query(EntityMuseum).order_by(EntityMuseum.created.desc()).all()

        count = objects.__len__()

    if first_m < 0:
        first_m = 0

    # if last_f isn't set (==-1), it is supposed to be an infinity
    if last_m == -1:
        museums = objects[first_m:]
    else:
        museums = objects[first_m: last_m + 1]

    if museums.__len__() == 0:
        if count > 0:
            if first_m > 0:
                first_m = min(int(first_m - math.fmod(first_m, 10)), int(count - math.fmod(count, 10)))
            elif first_m < 0:
                first_m = 0
            museums = objects[first_m: first_m + 10]
        else:
            first_m = 0
    page = int((first_m - math.fmod(first_m, 10)) / 10) + 1

    res = []
    for _ in museums:
        obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
        wide_info = EntityMuseum.get_wide_object(_.eid, ['image', 'game', 'location'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    res_dict = OrderedDict([('count', count), ('page', page), ('result', res)])

    resp.body = obj_to_json(res_dict)
    resp.status = falcon.HTTP_200


@admin_access_type_required
def addNewMuseum(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        params['ownerid'] = req.context['user_id']
        id = EntityMuseum.add_from_json(params)

        if id:
            objects = EntityMuseum.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
                wide_info = EntityMuseum.get_wide_object(_.eid, ['image', 'location'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


@admin_access_type_required
def updateMuseum(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    # email = req.context['email']
    # id_email = EntityUser.get_id_from_email(email)

    try:
        params = json.loads(req.stream.read().decode('utf-8'))

        # if params['id'] != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        id = EntityMuseum.update_from_json(params)

        if id:
            objects = EntityMuseum.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
                wide_info = EntityMuseum.get_wide_object(_.eid, ['image', 'location'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


@admin_access_type_required
def deleteMuseum(**request_handler_args):
    resp = request_handler_args['resp']
    req = request_handler_args['req']

    # TODO: VERIFICATION IF ADMIN DELETE ANY
    # email = req.context['email']
    id = getIntPathParam("Id", **request_handler_args)
    # id_email = EntityUser.get_id_from_email(email)

    if id is not None:
        # if id != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        res = []
        try:
            EntityMuseum.delete(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_404
            return

        try:
            EntityMuseum.delete_wide_object(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_405
            return

        object = EntityMuseum.get().filter_by(eid=id).all()
        if not len(object):
            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return

    resp.status = falcon.HTTP_400


def getMuseumById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("Id", **request_handler_args)
    objects = EntityMuseum.get().filter_by(eid=id).all()

    wide_info = EntityMuseum.get_wide_object(id, ['image', 'game', 'location'])

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


# end of museum feature set functions
# -----------------------------------

# Game feature set functions
# --------------------------


@admin_access_type_required
def deleteGame(**request_handler_args):
    resp = request_handler_args['resp']
    req = request_handler_args['req']

    # TODO: VERIFICATION IF ADMIN DELETE ANY
    # email = req.context['email']
    id = getIntPathParam("gameId", **request_handler_args)
    # id_email = EntityUser.get_id_from_email(email)

    if id is not None:
        # if id != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        res = []

        try:
            EntityGame.delete(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_404
            return

        try:
            EntityGame.delete_wide_object(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_405
            return

        object = EntityGame.get().filter_by(eid=id).all()
        if not len(object):
            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return

    resp.status = falcon.HTTP_400


@admin_access_type_required
def createGame(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        params['ownerid'] = req.context['user_id']
        id = EntityGame.add_from_json(params)

        if id:
            objects = EntityGame.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
                wide_info = EntityGame.get_wide_object(_.eid, ['image', 'scenario'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


@admin_access_type_required
def updateGame(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    # email = req.context['email']
    # id_email = EntityUser.get_id_from_email(email)

    try:
        params = json.loads(req.stream.read().decode('utf-8'))

        # if params['id'] != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        id = EntityGame.update_from_json(params)

        if id:
            objects = EntityGame.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
                wide_info = EntityGame.get_wide_object(_.eid, ['image', 'scenario'])
                obj_dict.update(wide_info)
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


def getGameById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("gameId", **request_handler_args)
    objects = EntityGame.get().filter_by(eid=id).all()

    wide_info = EntityGame.get_wide_object(id, ['image', 'scenario'])

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def GetAllGamesById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("ownerId", **request_handler_args)
    objects = EntityGame.get().filter_by(ownerid=id).all()

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'ownerid', 'name', 'desc'])
        wide_info = EntityGame.get_wide_object(_.eid, ['image', 'scenario'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def getGamesByMuseumId(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("museumId", **request_handler_args)
    if id is None:
        resp.body = obj_to_json({'error': 'Invalid parameter supplied'})
        resp.status = falcon.HTTP_400
        return

    quests = EntityMuseum.get_wide_object(id, ['game'])
    res = []
    if len(quests['game']):
        for _ in quests['game']:
            obj_dict = _
            wide_info = EntityGame.get_wide_object(int(_['eid']), ['image', 'scenario'])
            obj_dict.update(wide_info)
            res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


# End of game feature set functions
# ---------------------------------


# Scenario feature set functions
# --------------------------


@admin_access_type_required
def updateScenario(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))

        id, props = EntityScenario.update_from_json(params)

        res = []
        if id:
            res.append(props)
            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


def getScenarioById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("scenarioId", **request_handler_args)
    if id is None:
        resp.status = falcon.HTTP_400
        return

    objects = EntityScenario.get().filter_by(eid=id).all()

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'json'])
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


# End of scenario feature set functions
# ---------------------------------


# Token feature set functions
# ---------------------------


def getToken(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    type = getStringQueryParam('type', **request_handler_args)
    if type == 'swagger':
        query = parse_qs(req.stream.read().decode('utf-8'))
        redirect_uri = query['redirect_uri'][0]
        code = query['code'][0]
    else:
        redirect_uri = getStringQueryParam('redirect_uri', **request_handler_args)
        code = getStringQueryParam('code', **request_handler_args)

    if redirect_uri is None or code is None or type is None:
        resp.body = obj_to_json({'error': 'Invalid parameters supplied'})
        resp.status = falcon.HTTP_400
        return

    token, user, error, status = EntityToken.add_from_query({'redirect_uri': redirect_uri, 'code': code, 'type': type})

    if not error:
        token_dict = token.to_dict(['eid', 'access_token', 'type', 'user_id'])
        user_dict = user.to_dict(['name', 'image', 'email', 'access_type'])
        token_dict.update(user_dict)

        resp.body = obj_to_json(token_dict)
        resp.status = falcon.HTTP_200
        return

    resp.body = obj_to_json(error)
    resp.status = status


def getTokenInfo(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    access_token = getStringQueryParam('access_token', **request_handler_args)
    type = getStringQueryParam('type', **request_handler_args)

    if access_token is None or type is None:
        resp.body = obj_to_json({'error': 'Invalid parameters supplied'})
        resp.status = falcon.HTTP_400
        return

    token, user, error, status = EntityToken.update_from_query({'access_token': access_token, 'type': type})

    if not error:
        token_dict = token.to_dict(['eid', 'access_token', 'type', 'user_id'])
        user_dict = user.to_dict(['name', 'image', 'email', 'access_type'])
        token_dict.update(user_dict)

        resp.body = obj_to_json(token_dict)
        resp.status = falcon.HTTP_200
        return

    resp.body = obj_to_json(error)
    resp.status = status


def revokeToken(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    params = json.loads(req.stream.read().decode('utf-8'))

    res, status = EntityToken.delete_from_json(params)

    resp.body = obj_to_json(res)
    resp.status = status


# End of token feature set functions
# ----------------------------------


# Location feature set functions
# ------------------------------

@admin_access_type_required
def addLocation(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        id = EntityLocation.add_from_json(params)

        if id:
            objects = EntityLocation.get().filter_by(eid=id).all()

            res = []
            for _ in objects:
                obj_dict = _.to_dict()
                res.append(obj_dict)

            resp.body = obj_to_json(res)
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


@admin_access_type_required
def deleteLocation(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    res = []
    id = getIntPathParam("locationId", **request_handler_args)
    if id is None:
        resp.status = falcon.HTTP_400
        return

    try:
        EntityLocation.delete(id)
    except FileNotFoundError:
        resp.status = falcon.HTTP_404
        return

    object = EntityLocation.get().filter_by(eid=id).all()
    if not len(object):
        resp.body = obj_to_json(res)
        resp.status = falcon.HTTP_200
        return

    resp.status = falcon.HTTP_400


def getTapeLocations(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    first_l = getIntQueryParam('FirstLocation', **request_handler_args)
    last_l = getIntQueryParam('LastLocation', **request_handler_args)

    with DBConnection() as session:
        objects = session.db.query(EntityLocation).order_by(EntityLocation.name).all()
        count = objects.__len__()

    if first_l < 0:
        first_l = 0

    # if last_f isn't set (==-1), it is supposed to be an infinity
    if last_l == -1:
        locations = objects[first_l:]
    else:
        locations = objects[first_l: last_l + 1]

    if locations.__len__() == 0:
        if count > 0:
            if first_l > 0:
                first_l = min(int(first_l - math.fmod(first_l, 10)), int(count - math.fmod(count, 10)))
            elif first_l < 0:
                first_l = 0
            locations = objects[first_l: first_l + 10]
        else:
            first_l = 0
    page = int((first_l - math.fmod(first_l, 10)) / 10) + 1

    res = []
    for _ in locations:
        obj_dict = _.to_dict()
        res.append(obj_dict)

    res_dict = OrderedDict([('count', count), ('page', page), ('result', res)])

    resp.body = obj_to_json(res_dict)
    resp.status = falcon.HTTP_200


def findLocationByName(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    start = getStringQueryParam("startswith", **request_handler_args)
    if start is None:
        resp.status = falcon.HTTP_400
        return
    with DBConnection() as session:
        objects = session.db.query(EntityLocation).filter(EntityLocation.name.startswith(start)).all()

    res = []
    for _ in objects:
        obj_dict = _.to_dict()
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


# End of location feature set functions
# -------------------------------------

operation_handlers = {
    # Museums
    'getAllMuseumsMockup':  [getAllMuseumsMockup],
    'getAllMuseums':        [getAllMuseums],
    'getTapeMuseums':       [getTapeMuseums],
    'addNewMuseum':         [addNewMuseum],
    'updateMuseum':         [updateMuseum],
    'deleteMuseum':         [deleteMuseum],
    'getMuseum':            [getMuseumById],

    # Games
    'getGamesByMuseumId':   [getGamesByMuseumId],
    'getAllGamesById':      [GetAllGamesById],
    'getGameById':          [getGameById],
    'addNewGame':           [createGame],
    'updateGame':           [updateGame],
    'deleteGame':           [deleteGame],

    # Feed
    'getFeedMockup':        [getFeedMockup],
    'addFeed':              [addFeed],
    'updateFeed':           [updateFeed],
    'getTapeFeeds':         [getTapeFeeds],
    'getAllFeeds':          [getAllFeeds],
    'getFeed':              [getFeedById],
    'deleteFeed':           [deleteFeed],

    # OAuth
    'getToken':             [getToken],
    'getTokenInfo':         [getTokenInfo],
    'revokeToken':          [revokeToken],

    # Location
    'addLocation':          [addLocation],
    'deleteLocation':       [deleteLocation],
    'getTapeLocations':     [getTapeLocations],
    'findLocationByName':   [findLocationByName],

    # Scenario
    'getScenarioById':      [getScenarioById],
    'updateScenario':       [updateScenario],

    'getVersion':           [getVersion],
    'httpDefault':          [httpDefault]
}


class CORS(object):
    def process_response(self, req, resp, resource):
        origin = req.get_header('Origin')
        if origin:
            resp.set_header('Access-Control-Allow-Origin', origin)
            resp.set_header('Access-Control-Max-Age', '100')
            resp.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
            resp.set_header('Access-Control-Allow-Credentials', 'true')

            acrh = req.get_header('Access-Control-Request-Headers')
            if acrh:
                resp.set_header('Access-Control-Allow-Headers', acrh)

            # if req.method == 'OPTIONS':
            #    resp.set_header('Access-Control-Max-Age', '100')
            #    resp.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
            #    acrh = req.get_header('Access-Control-Request-Headers')
            #    if acrh:
            #        resp.set_header('Access-Control-Allow-Headers', acrh)


class Auth(object):
    def process_request(self, req, resp):
        #TODO: SWITCH ON
        #req.context['email'] = 'serbudnik@gmail.com'
        #return
        # skip authentication for version, UI and Swagger
        if re.match('(/each/version|'
                     '/each/settings/urls|'
                     '/each/images|'
                     '/each/ui|'
                     '/each/swagger\.json|'
                     '/each/swagger-temp\.json|'
                     '/each/swagger-ui|'
                     '/each/feed/all|'
                     '/each/feed/tape|'
                     '/each/museum/tape|'
                     '/each/museum/all|'
                     '/each/token/get).*', req.relative_uri):
            return

        with DBConnection() as session:
            news = session.db.query(EntityNews.eid, PropInt.value) \
                .join(PropInt, PropInt.eid == EntityNews.eid) \
                .order_by(PropInt.value.desc(), EntityNews.created.desc()).all()[0:10]
            res = [str(_[0]) for _ in news]
            regexes = '/each/feed/(%s)' % '|'.join(res)
            if re.fullmatch(regexes, req.relative_uri) and req.method == 'GET':
                return

        if req.method == 'OPTIONS':
            return # pre-flight requests don't require authentication

        token = None
        try:
            if req.auth:
                token = req.auth.split(" ")[1].strip()
                if len(req.auth.split(" ")) > 2:
                    type = req.auth.split(" ")[2].strip()
                else:
                    type = 'swagger'
            else:
                raise falcon.HTTPUnauthorized(description='Token was not provided in schema [bearer <Token>]',
                                              challenges=['Bearer realm=http://GOOOOGLE'])
        except:
            raise falcon.HTTPUnauthorized(description='Token was not provided in schema [bearer <Token>]',
                                          challenges=['Bearer realm=http://GOOOOGLE'])

        error = 'Authorization required.'
        if token:
            error, acc_type, user_email, user_id, user_name = auth.Validate(
                token,
                type
            )

            if not error:
                req.context['user_email'] = user_email
                req.context['user_id'] = user_id
                req.context['user_name'] = user_name
                req.context['access_type'] = acc_type

                return # passed access token is valid

        raise falcon.HTTPUnauthorized(description=error,
                                      challenges=['Bearer realm=http://GOOOOGLE'])


logging.getLogger().setLevel(logging.DEBUG)
args = utils.RegisterLaunchArguments()

cfgPath = args.cfgpath
profile = args.profile

# configure
with open(cfgPath) as f:
    cfg = utils.GetAuthProfile(json.load(f), profile, args)
    DBConnection.configure(**cfg['each_db'])
    if 'oidc' in cfg:
        cfg_oidc = cfg['oidc']

general_executor = ftr.ThreadPoolExecutor(max_workers=20)

# change line to enable OAuth autorization:
wsgi_app = api = falcon.API(middleware=[CORS(), Auth(), MultipartMiddleware()])
#wsgi_app = api = falcon.API(middleware=[CORS(), MultipartMiddleware()])

server = SpecServer(operation_handlers=operation_handlers)

if 'server_host' in cfg:
    with open('swagger.json') as f:
        swagger_json = json.loads(f.read(), object_pairs_hook=OrderedDict)

    server_host = cfg['server_host']
    swagger_json['host'] = server_host

    baseURL = '/each'
    if 'basePath' in swagger_json:
        baseURL = swagger_json['basePath']

    EntityBase.host = server_host + baseURL
    EntityBase.MediaCls = EntityMedia
    EntityBase.MediaPropCls = PropMedia

    json_string = json.dumps(swagger_json)

    with open('swagger_temp.json', 'wt') as f:
        f.write(json_string)

with open('swagger_temp.json') as f:
    server.load_spec_swagger(f.read())

api.add_sink(server, r'/')
