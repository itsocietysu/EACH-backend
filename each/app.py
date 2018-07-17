import concurrent.futures as ftr
import json
import logging
import mimetypes
import os
import posixpath
import re
import time
from collections import OrderedDict

import falcon
from falcon_multipart.middleware import MultipartMiddleware

from each import utils
from each.db import DBConnection
from each.serve_swagger import SpecServer
from each.utils import obj_to_json, getIntPathParam
from each.Entities.EntityUser import EntityUser
from each.Entities.EntityBase import EntityBase
from each.Entities.EntityMedia import EntityMedia
from each.Entities.EntityNews import EntityNews

from each.Prop.PropMedia import PropMedia
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

def getAllMuseums(**request_handler_args):
    resp = request_handler_args['resp']
    resp.status = falcon.HTTP_200
    with open("museum.json") as f:
        resp.body = f.read()

def getFeed(**request_handler_args):
    resp = request_handler_args['resp']
    resp.status = falcon.HTTP_200
    with open("feed.json") as f:
        resp.body = f.read()


def createUser(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        id = EntityUser.add_from_json(params)

        if id:
            objects = EntityUser.get().filter_by(eid=id).all()

            resp.body = obj_to_json([o.to_dict() for o in objects])
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


def updateUser(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    #email = req.context['email']
    #id_email = EntityUser.get_id_from_email(email)

    try:
        params = json.loads(req.stream.read().decode('utf-8'))

        #if params['id'] != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        id = EntityUser.update_from_json(params)

        if id:
            objects = EntityUser.get().filter_by(eid=id).all()

            resp.body = obj_to_json([o.to_dict() for o in objects])
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


def getAllUsers(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    objects = EntityUser.get().all()

    resp.body = obj_to_json([o.to_dict() for o in objects])
    resp.status = falcon.HTTP_200


def getUserById(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    id = getIntPathParam("userId", **request_handler_args)
    objects = EntityUser.get().filter_by(eid=id).all()

    wide_info = EntityUser.get_wide_object(id, ['private', 'avatar'])

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'login'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def getMyUser(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    e_mail = req.context['email']
    id = EntityUser.get_id_from_email(e_mail)

    objects = EntityUser.get().filter_by(eid=id).all()

    # TODO: LIMIT the posts output counts with a paging
    wide_info = EntityUser.get_wide_object(id, ['private', 'avatar', 'post'])

    wide_info['post'].sort(key=lambda x: x['eid'], reverse=True)

    res = []
    for _ in objects:
        obj_dict = _.to_dict(['eid', 'login'])
        obj_dict.update(wide_info)
        res.append(obj_dict)

    resp.body = obj_to_json(res)
    resp.status = falcon.HTTP_200


def deleteUser(**request_handler_args):
    resp = request_handler_args['resp']
    req = request_handler_args['req']

    # TODO: VERIFICATION IF ADMIN DELETE ANY
    #email = req.context['email']
    id = getIntPathParam("userId", **request_handler_args)
    #id_email = EntityUser.get_id_from_email(email)

    if id is not None:
        #if id != id_email or not EntitySuperUser.is_id_super_admin(id_email):
        #    resp.status = falcon.HTTP_403
        #    return

        try:
            EntityUser.delete(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_404
            return

        try:
            EntityUser.delete_wide_object(id)
        except FileNotFoundError:
            resp.status = falcon.HTTP_405
            return

        object = EntityUser.get().filter_by(eid=id).all()
        if not len(object):
            resp.status = falcon.HTTP_200
            return

    resp.status = falcon.HTTP_400


def addFeed(**request_handler_args):
    req = request_handler_args['req']
    resp = request_handler_args['resp']

    try:
        params = json.loads(req.stream.read().decode('utf-8'))
        id = EntityNews.add_from_json(params)

        if id:
            objects = EntityNews.get().filter_by(eid=id).all()

            resp.body = obj_to_json([o.to_dict() for o in objects])
            resp.status = falcon.HTTP_200
            return
    except ValueError:
        resp.status = falcon.HTTP_405
        return

    resp.status = falcon.HTTP_501


operation_handlers = {
    # Users
    'createUser':           [createUser],
    'updateUser':           [updateUser],
    'getAllUsers':          [getAllUsers],
    'getUser':              [getUserById],
    'getMyUser':            [getMyUser],
    'deleteUser':           [deleteUser],

    # Museums
    'getAllMuseums':        [getAllMuseums],

    # Feed
    'getFeed':              [getFeed],
    'addFeed':              [addFeed],

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
                     '/each/swagger-ui).*', req.relative_uri):
            return

        if req.method == 'OPTIONS':
            return # pre-flight requests don't require authentication

        token = None
        try:
            if req.auth:
                token = req.auth.split(" ")[1].strip()
            else:
                token = req.params.get('access_token')
        except:
            raise falcon.HTTPUnauthorized(description='Token was not provided in schema [berear <Token>]',
                                      challenges=['Bearer realm=http://GOOOOGLE'])

        error = 'Authorization required.'
        if token:
            error, res, email = auth.Validate(token, auth.PROVIDER.GOOGLE)
            if not error:
                req.context['email'] = email

                if not EntityUser.get_id_from_email(email) and not re.match('(/each/user).*', req.relative_uri):
                    raise falcon.HTTPUnavailableForLegalReasons(description=
                                                                "Requestor [%s] not existed as user yet" % email)

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

wsgi_app = api = falcon.API(middleware=[CORS(), MultipartMiddleware()])# , Auth()

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
