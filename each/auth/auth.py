#from each.auth.config import CONFIG, PROVIDER

import urllib.request
import json

#def Configure(**kwargs):
#    CONFIG.update(kwargs)


def Validate(url, token, type):
    try:
        response = urllib.request.urlopen('%s?access_token=%s&type=%s' % (url, token, type))
        certs = response.read().decode()
        json_load = json.loads(certs)
        return None, json_load['access_type'], json_load['email'], json_load['user_id'], json_load['name']
    except Exception as e:
        return str(e), None, None, None, None
