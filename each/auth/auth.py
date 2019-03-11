#from each.auth.config import CONFIG, PROVIDER

import falcon

from each.Entities.EntityToken import EntityToken, EntityUser

#def Configure(**kwargs):
#    CONFIG.update(kwargs)


def Validate(access_token, type):
    try:
        token, user, error, status = EntityToken.update_from_query({'access_token': access_token, 'type': type})
        if error:
            return error['error'], None, None, None, None
        return None, user['access_type'], user['email'], token['user_id'], user['name']
    except Exception as e:
        return str(e), None, None, None, None
