from jose import jwt

oidc_params = {
    'client_id': 'star',
    'client_secret': 'a72581e1-09be-4cb0-9959-6b957372f749',
    'realm': 'http://10.66.13.213:8180/auth/realms/star-realm'
}

JWT_SIGN_ALGORITHM = 'RS256'
JWT_PUBLIC_KEY = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2306g4lK+eGXGCHABrCp
Qh/kds9Aky13xeGCzgILUesyi5yvxiqi8AVuVvxQ3cM5JZZRxbIPOYqjISSQi5qm
xqxtkd2nVmgewHYbLUEkEpt4x57mfvEitST2PvLjjF1aAnwtM/QUw4vgjNtBjS4y
yAGKvHGx8UXxKv9O1RlaA7JLOx0qYEpbnx1f8R7f8q3kIS18xem7COOnpvfol9sd
oGSaqxg+Dtcqw+w23fYkn/BrkH0fvuIW0r8ypMTopTfE+0rQcAEJ8Zs+86aNYHnp
CHnH3akf3XIHEwdEcPs+tv2O4Iz0aS7NK9NfnVpe2RP1ePnJPo9R0DhLuQynrqKc
PQIDAQAB
-----END PUBLIC KEY-----'''

def Configure(**kwargs):
    oidc_params.update(kwargs)

def Validate(token):
    try:
        aud = jwt.get_unverified_claims(token).get('aud')  # we accept whatever audience encoded in the token
        res = jwt.decode(token, JWT_PUBLIC_KEY, issuer=oidc_params['realm'], audience=aud,
                         algorithms=JWT_SIGN_ALGORITHM)
        return None, res

    except jwt.JWTError as e:
        return str(e), None
