#from each.auth.config import CONFIG, PROVIDER

import falcon

from each.Entities.EntityToken import EntityToken, EntityUser

#def Configure(**kwargs):
#    CONFIG.update(kwargs)


def Validate(access_token, type):
    try:
        res, status = EntityToken.update_from_query({'access_token': access_token, 'type': type})
        if status != falcon.HTTP_200:
            return res['error'], None, None, None, None
        token = EntityToken.get().filter_by(eid=res).first()
        user = EntityUser.get().filter_by(eid=token.user_id).first()
        return None, user['access_type'], user['email'], token['user_id'], user['name']
    except Exception as e:
        return str(e), None, None, None, None
