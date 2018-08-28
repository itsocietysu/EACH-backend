import os
import logging
import datetime
import argparse
import base64
import requests
import json
import falcon

def obj_to_json(obj):
    return json.dumps(obj, indent=2)


def _DateToString(datetime):
    return datetime.ctime()

def batch(iterable, batch_size):
    b = []
    for item in iterable:
        b.append(item)
        if len(b) == batch_size:
            yield b
            b = []

    if len(b) > 0:
        yield b

def getPathParam(name, **request_handler_args):
    return request_handler_args['uri_fields'][name].partition('?')[0]

def getIntPathParam(name, **request_handler_args):
    s = getPathParam(name, **request_handler_args)
    try:
        return int(s)
    except ValueError:
        return None

def getQueryParam(name, **request_handler_args):
    try:
        return request_handler_args['req'].params[name]
    except KeyError:
        return 0 if name == 'FirstFeed' else -1

def getIntQueryParam(name, **request_handler_args):
    s = getQueryParam(name, **request_handler_args)
    try:
        return int(s)
    except ValueError:
        return None

def isAllInData(params, data):
    return all([(_ in data) for _ in params])

# def ReadEntireLobs(entire_tuple):
#     result = []
#     for item in entire_tuple:
#         if isinstance(item, cx_Oracle.LOB):
#             item = item.read()
#         result.append(item)
#     return tuple(result)

def GetAuthProfile(jso, profile_name="local", args=None):
    ret = None
    if "profiles" in jso:
        for item in jso["profiles"]:
            if item["name"] == profile_name:
                ret = item
    elif "each_db" in jso and "oidc" in jso:
        ret = jso

    if not ret:
        raise ConnectionAbortedError('Config file format is wrong')

    if args:
        ret['each_db']['user']      = ret['each_db']['user']        if not args.dbuser else args.dbuser
        ret['each_db']['sid']       = ret['each_db']['sid']         if not args.dbsid  else args.dbsid
        ret['each_db']['password']  = ret['each_db']['password']    if not args.dbpswd else args.dbpswd
        ret['each_db']['host']      = ret['each_db']['host']        if not args.dbhost else args.dbhost
        ret['each_db']['port']      = ret['each_db']['port']        if not args.dbport else args.dbport

    return ret

def RegisterLaunchArguments():
    parser = argparse.ArgumentParser(description='Serve the each server')
    parser.add_argument('--profile', help='clarify the profile in config.json to use', default='local')
    parser.add_argument('--cfgpath', help='overrides the default path to config.json', default='./config.json')
    parser.add_argument('--dbsid', help='overrides the DB SID in config.json')
    parser.add_argument('--dbuser', help='overrides the DB USER in config.json')
    parser.add_argument('--dbpswd', help='overrides the DB PASSWORD in config.json')
    parser.add_argument('--dbhost', help='overrides the DB HOST in config.json')
    parser.add_argument('--dbport', help='overrides the DB PORT in config.json')

    return parser.parse_args()

class IterStream(object):
    "File-like streaming iterator."

    def __init__(self, generator):
        self.generator = generator
        self.iterator = iter(generator)
        self.leftover = b''

    def __len__(self):
        return self.generator.__len__()

    def __iter__(self):
        return self.iterator

    def __next__(self):
        return next(self.iterator)

    def read(self, size):
        data = self.leftover
        count = len(self.leftover)
        try:
            while count <= size:
                chunk = next(self)
                data += chunk
                count += len(chunk)
        except StopIteration:
            self.leftover = b''
            return data

        if count > size:
            self.leftover = data[size:]

        return data[:size]


def to_base64_safe(str):
    return base64.b64encode(str.encode()).decode("UTF-8")

def from_base64_safe(str):
    try:
        res = base64.b64decode(str.encode()).decode("UTF-8")
    except:
        res = str

    return res

def GetItemByPath(dic, path):
    v = dic
    for k in path.split("/"):
        if not v or not isinstance(v, dict):
            return
        v = v.get(k)

    return v

def admin_access_type_required(func_to_set_access):
    def check_access_type(**arg):
        if arg['req'].context['access_type'] == 'admin':
            return func_to_set_access(**arg)
        else:
            arg['resp'].status = falcon.HTTP_423
            return
    return check_access_type
