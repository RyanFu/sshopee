import requests, hashlib, random
from api_tools import multiple_mission_pool, mydb

url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
appid = '20171115000095737'
appkey = 'dfKYJL8LaQNTdX1vOJi2'
cache = {}

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
    cache[q] = re
    return re

def mass_translate(qs):
    values = [(q,) for q in qs]
    multiple_mission_pool(translate, values, 10)
    rs = [cache.get(q, None) for q in qs]
    return rs

if __name__ == '__main__':
    sql = 'select name from items where account like "%.th" limit 100'
    con = mydb(sql)
    qs = [i[0] for i in con]
    rs = mass_translate(qs)
    for q, r in zip(qs, rs):
        print(q, r)