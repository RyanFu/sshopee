import requests, hashlib, random

url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
appid = '20171115000095737'
appkey = 'dfKYJL8LaQNTdX1vOJi2'


def sigh(q, salt):
    s = appid + q + salt + appkey
    md5 = hashlib.md5()
    md5.update(s.encode('utf-8'))
    r = md5.hexdigest()
    return r

def translate(q):
    salt = str(random.randint(10000000, 999999999))
    params = {
    'q': q,
    'from': 'auto',
    'to': 'en',
    'appid': appid,
    'salt': salt,
    'sign': sigh(q, salt),
    }

    re = requests.get(url, params)
    re = re.json()['trans_result'][0]['dst']
    print(q, re)
    return re

