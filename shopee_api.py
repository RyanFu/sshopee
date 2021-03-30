#coding=utf-8  
import api_sklearn
import json, requests, time, platform
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from api_tools import multiple_mission_pool, decor_retry, decor_async, snow, mydb

if platform.system() == "Windows":
    database_name = "D:/shopee.db"
    driver_path = 'D:/chromedriver_win32/chromedriver.exe'
else:
    database_name = "/root/shopee.db"
    driver_path = "/root/chromedriver.exe"

ua = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"
headers = {'User-Agent': ua}
#http://chromedriver.storage.googleapis.com/index.html

def host(site):
    url = "https://seller.{}.shopee.cn".format(site)
    return url


#使用SELENIUM控制CHORME打开账号后台
def open_sellercenter(account, password, cookie_only=True):
    if driver_path == "/root/chromedriver.exe":
        cookie_only = True
    site = account[-2:]
    ch_options = Options()
    if cookie_only:
        ch_options.add_argument("--headless")
        ch_options.add_argument("--no-sandbox")
        print("no head")

    driver = webdriver.Chrome(executable_path=driver_path, options=ch_options)
    driver.get(host(site) + '/account/signin')
    print("find login page")
    WebDriverWait(driver, timeout=30).until(lambda d: d.find_element_by_tag_name("input"))
    bs = driver.find_elements_by_tag_name('input')
    bs[0].send_keys(account)
    bs[1].send_keys(password)
    try:
        driver.find_element_by_tag_name('button').click()
    except:
        element = driver.find_element_by_tag_name('button')
        driver.execute_script("arguments[0].click();", element)
    print("login done")
    WebDriverWait(driver, timeout=30).until(lambda d: d.find_element_by_class_name("card"))
    cookies_raw = driver.get_cookies()
    if cookie_only:  
        driver.quit()

    cookies_dict = {}
    for i in cookies_raw:
        k = i["name"]
        v = i["value"]
        cookies_dict[k] = v

    cookies_text = json.dumps(cookies_dict) 
    sql = "insert or replace into cookies values(?, ?, ?)"
    mydb(sql, [account, cookies_text, snow()])
    return cookies_text

#检查COOKIES有效性,失效则更新
def check_cookie_jar(account):
    sql = "select cookies from cookies where account = ?"
    con = mydb(sql, [account])        
    if con:
        cookie_dict = json.loads(con[0][0])
        site = account.split(".")[1]  
        url = host(site) + "/api/v3/product/page_product_list"
        params = "/?source=seller_center&page_size=12&version=3.2.0&page_number=1"
        data = requests.get(url+params, cookies=cookie_dict, headers=headers).json()
        message = data["message"]
        if message == "success":
            print(account, " cookies still usable")
        else:
            print(account, " cookies invalid, update now")
            con = None
    else:
        print(account, ' cookies not found, go get it now')
    if not con:
        sql = 'select password from password where account = ?'
        con = mydb(sql, [account,])
        password = con[0][0]
        open_sellercenter(account, password, True)
    print(account, ' cookies updated')
    return

#获取账号COOKIES
def get_cookie_jar(account):
    sql = "select cookies from cookies where account = ?"
    con = mydb(sql, [account])        
    cookie_dict = json.loads(con[0][0])
    cookie_jar = requests.utils.cookiejar_from_dict(cookie_dict)
    return cookie_dict


def get_performance(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account)
    url = host(site) + "/api/v3/general/get_shop"
    data = requests.get(url, cookies=cookies, headers=headers).json()["data"]
    follower_count = data["follower_count"]
    item_count = data["item_count"]
    rating_count = data["rating_bad"] + data["rating_good"] + data["rating_normal"]
    url = host(site) + "/api/v2/shops/sellerCenter/ongoingPoints"
    data = requests.get(url, cookies=cookies, headers=headers).json()["data"]
    totalPoints = data["totalPoints"]
    url = host(site) + "/api/v2/shops/sellerCenter/shopPerformance"
    data = requests.get(url, cookies=cookies, headers=headers).json()["data"]
    #print(data)
    values = [
        follower_count, #0
        item_count, #1
        data["customerSatisfaction"][0]["my"], #2
        rating_count, #3
        data["listingViolations"][1]["my"], #4
        totalPoints, #5
        data["customerService"][0]["my"], #6
        data["fulFillMent"][0]["my"], #7
        data["fulFillMent"][0]["children"][0]["my"], #8
        data["fulFillMent"][0]["children"][1]["my"], #9
        data["fulFillMent"][2]["my"], #10
        data["fulFillMent"][1]["my"], #11
    ]
    i_list = [2, 4, 6, 7, 8, 9, 10, 11]
    for i in i_list:
        try:
            values[i] = int(values[i]) / 1000000
        except:
            values[i] = 0
    values[-2] *= 10
    values.insert(0, account)
    values.append(snow())
    ph = ["?" for i in values]
    ph = ", ".join(ph)
    sql = "insert or replace into performance values ({ph})".format(ph=ph)
    print(sql, values)
    mydb(sql, values)
    return values

def get_all_performance():
    sql = 'select account from password'
    con = mydb(sql)
    account_list = [i[0] for i in con]
    for account in account_list:
        check_cookie_jar(account)
    multiple_mission_pool(get_performance, con)
    return

#单面产品列表转换格式
def convert_page_list(page):
    key_list = ['id', 'parent_sku', 'pre_order', 'status','name', 'price_before_discount', 'price', 'stock', 
    'view_count', 'sold','like_count','rating_star','rating_count']
    
    for i in page:
        i['price_before_discount'] = i['price_info']['input_normal_price']
        i['price'] = i['price_info']['input_promotion_price']
        for j in i['model_list']:
            j['price_before_discount'] = j['price_info']['input_normal_price']
            j['price'] = j['price_info']['input_promotion_price']

    row_list = [key_list]
    for  i in page:
        if i['status'] == 4:
            continue
        i['create_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(i['create_time'])))
        i['modify_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(i['modify_time'])))
        i['rating_count'] = sum(i['rating_count'])

        row = [i[k] for k in key_list]
        row.append(".".join(str(e) for e in i['category_path']))
        row.append(i['create_time'])
        row.append(len(i['images']))
        if len(i['model_list']) > 0:
            for m in i['model_list']:
                mr = [];
                mks = ['id', 'sku', 'name','price_before_discount','price', 'sold', 'stock']
                mr = [ m[mk] for mk in mks]                
                final_row =row + mr
                row_list.append(final_row)
        else:
            final_row = row
            row_list.append(final_row)
    return row_list

#单个页面产品获取并保存, 加锁
@decor_retry
def get_single_page(account, cookies, page_num, dp=False):
    site = account.split(".")[1]  
    url = host(site) + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=48&version=3.2.0&page_number={num}".format(num=page_num)      
    data = requests.get(url+params, cookies=cookies, headers=headers).json()
    print(data["message"])
    total_count = data["data"]["page_info"]["total"]
    page = data["data"]["list"]
    row_list = convert_page_list(page)
    for row in row_list:
        row.append(account)
        row.append(snow())

    rows = row_list[1:]
    sql = "insert into items values (?" + ",?" * 24 + ")"
    mydb(sql, rows, True)
    print(time.ctime(), account, "add items complete")

    conplete_count = page_num * 48
    if conplete_count <= total_count:
        print("complete listng count ", conplete_count)

#更新账号产品
#@decor_retry
def get_all_page(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account)
    url = host(site) + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=12&version=3.2.0&page_number=1"
    data = requests.get(url+params, cookies=cookies, headers=headers).json()
    message = data["message"]
    total_count = data["data"]["page_info"]["total"]
    total_page = total_count // 48 + 1
    mydb('delete from items where account = ?', (account,))
    num_list = [[account, cookies, i] for i in range(1, total_page + 1)]
    multiple_mission_pool(get_single_page, num_list)
    mydb('delete from items where status > 3')
    mydb('update items set model_current_price = model_original_price where model_current_price  = 0')
    return

   
@decor_async
def tm_task_list():
    host = "http://182.61.49.48:5000/"
    task_list = [ 
    "/update_all_shop_performance",
    "/update_all_accounts_listings",
    "/listings_count",
    "/get_cancellation_orders",
    "/get_return_orders",
    "/ad_report",
    ]
    for task in task_list:
        url = host + task
        requests.get(url, timeout=None)   
    return
    

@decor_async
def mytimer():
    while True:        
        h = time.localtime().tm_hour
        if h == 0:
            print(time.ctime(), "start updating listings")   
            tm_task_list()
        else:
            print("waiting...")
        time.sleep(60*60)
 
    
#获取取消订单
def get_cancellations_by_account(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account) 
    url = host(site) + '/api/v3/order/get_simple_order_ids'
    params = {
    'SPC_CDS_VER':2,
    'source':'cancelled_to_respond',
    'page_size':40,
    'page_number':1,
    'total':0,
    'is_massship':False
    }
    data = requests.get(url, params=params,cookies=cookies, headers=headers).json()
    orders = data['data']['orders'] #shop_id,order_id
    print(account, len(orders))
    order_ids = [str(i['order_id']) for i in orders]
    order_ids = ','.join(order_ids)
    url = host(site) + '/api/v3/order/get_compact_order_list_by_order_ids'
    params = {'SPC_CDS_VER':2, 'order_ids':order_ids}
    data = data = requests.get(url, params=params,cookies=cookies, headers=headers).json()
    orders = data['data']['orders'] 
    #cancellation_end_date,order_sn,order_id,shop_id
    values = [[account, i['order_id'], i['order_sn'], i['cancellation_end_date'], snow()] for i in orders]
    sql = '''insert into cancellation (account,order_id,order_sn,cancellation_end_date,update_time) 
    values (?, ?, ?, ?, ?)'''
    mydb(sql, values, True)
    return

def get_all_cancellations():
    mydb('delete from cancellation')
    cu = mydb('select account from password')
    account_list = [i for i in cu]
    multiple_mission_pool(get_cancellations_by_account, account_list, 32)
    return
      
def cancellation_reject_accept(account, order_id, action):
    #account, order_id, action = 'jihuishi.my', 65371133466290, 'accept'
    site = account[-2:]
    url = host(site) + '/api/v3/order/respond_cancel_request'
    data = {'order_id':order_id, 'action': action}
    cookies = get_cookie_jar(account)
    res = requests.post(url, data=data, cookies=cookies)
    print(order_id, res.json(),res.status_code)
    return res.json()

def get_returns_by_account(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account) 
    url = host(site) + '/api/v1/return/list'
    params = '?SPC_CDS_VER=2&page_size=40&refund_status=refund_unprocessed'
    data = requests.get(url+params, cookies=cookies, headers=headers).json()
    returns = data['data']['list']
    values = []
    rt = {1:"商品未收到",
        2:"收到不对的商品",
        4:"商品与叙述不符",
        103:"收到不完整商品",
        106:"商品损坏",
        107:"商品部分功能无法使用"}
    for i in returns:
        #print(i)
        rv = [account, i['order_id'], i['return_id'], i['return_sn'], 
        i['reason'], 0, i['refund_amount'], snow() ]
        rv[5] = i['return_header']['attribute_list']['return_attributes'][2]['value']
        rv[5] = snow(int(rv[5]))
        rv[4] = rt.get(int(rv[4]), rt[4])
        values.append(rv)
    mydb('delete from return where account = ?', (account,))
    sql = '''insert into return (account, order_id, return_id, return_sn,
    reason, refund_end_date,refund_amount,update_time) values (?,?,?,?,?,?,?,?)'''
    mydb(sql, values, True)

def get_all_returns():
    cu = mydb('select account from password')
    account_list = [i for i in cu]
    multiple_mission_pool(get_returns_by_account, account_list, 32)
    return

def sn2details(account, sn):
    site = account[-2:]
    cookies = get_cookie_jar(account)
    url = host(site) + "/api/v3/order/get_order_hint"
    params = {"keyword": sn, "query": sn}
    data = requests.get(url, params=params, cookies=cookies).json()
    #print(data)
    if len(data['data']['orders']) > 0:
        order_id = data['data']['orders'][0]['order_id']
        status = data['data']['orders'][0]['status']
    else:
        order_id, status = None, None
    channels = {"my": 28016,"id": 88001,"th": 78004,"ph": 48002,"vn": 58007,"sg": 18025, "br": 90001}
    channel_id = channels[site]
    url = host(site) + "/api/v3/shipment/init_order"
    payload = {"channel_id":channel_id,"order_id":order_id,"forder_id":order_id}
    data = requests.post(url, payload, cookies=cookies).json()
    message = data["user_message"]
    #print(data)
    data = {"order_id": order_id, "status": status, "tracking_message":message}
    return data

def get_recommend_category_one(name, site, cookies, mp):
    url = host(site) +  "/api/v3/category/get_recommend_category"
    params = {"version": "3.1.0", "name": name}
    data = requests.get(url, params=params, cookies=cookies).json()
    cats = data['data']['cats']
    if cats:
        cat = cats[0]
        cat_id = cat[-1]
    else:
        cat_id = 0
    mp[name] = cat_id
    return cat_id

def shopee_recommend_category(name_list, account):
    cookies = get_cookie_jar(account)
    site = account[-2:]
    mp = {}
    values = [[name, site, cookies, mp] for name in name_list]
    multiple_mission_pool(get_recommend_category_one, values)
    return mp

def recommend_category(name_list, account):
    site = account[-2:]
    rare = ['br', 'mx', 'sg']
    model_name = 'my' if site in rare else site
    cat_id_ai = api_sklearn.pipe_predict(name_list, model_name)
    if site in rare:
        sql = 'select my, {} from cat_map'.format(site)
        con = mydb(sql)
        mp = {}
        for r in con:
            mp[r[0]] = r[1]
        cat_id_ai = [mp.get(int(i), 0) for i in cat_id_ai]
    sql = 'select catid, cat1, cat2, cat3 from catname where site=?'
    con = mydb(sql, (site,))
    mp = {}
    for r in con:
        mp[r[0]] = '/'.join(r[1:])
    #print(mp)
    cat_name_ai = [mp.get(int(i), []) for i in cat_id_ai]
    data = list(zip(name_list, cat_id_ai, cat_name_ai))
    return data

def recommend_category_backup(name_list, account):
    site = account[-2:]
    model_name = site
    mp = shopee_recommend_category(name_list, account)
    cat_id_ai = api_sklearn.pipe_predict(name_list, model_name)
    cat_id_shopee = [mp[i] for i in name_list]
    sql = 'select catid, cat1, cat2, cat3 from catname where site=?'
    con = mydb(sql, (site,))
    mp = {}
    for r in con:
        mp[r[0]] = '/'.join(r[1:])
    #print(mp)
    cat_name_ai = [mp.get(int(i), []) for i in cat_id_ai]
    cat_name_shopee = [mp.get(int(i), []) for i in cat_id_shopee]
    data = list(zip(name_list, cat_id_shopee, cat_name_shopee, cat_id_ai, cat_name_ai))
    return data

def update_listing(account, cookies, item_id, model_id, stock):    
    cookies = get_cookie_jar(account)
    site = account[-2:]
    url = host(site) + "/api/v3/product/get_product_detail"
    params = "/?SPC_CDS_VER=2&product_id=" + str(item_id)
    res = requests.get(url + params, cookies=cookies)
    data = res.json()['data']
    #print(data)
    chs = {
        "my": [{"size":0,"price":"5.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":28016,"sizeid":0}],
        "id": [{"size":0,"price":"10000.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":88001,"sizeid":0}],
        "th": [{"size":0,"price":"20","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":78004,"sizeid":0}],
        "ph": [{"size":0,"price":"40","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":48002,"sizeid":0}],
        "vn": [{"size":0,"price":"10000","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":58007,"sizeid":0}],
        "sg": [{"size":0.02,"price":"0.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18028,"sizeid":0}],
        "br": [{"size":0,"price":"15","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":90001,"sizeid":0}],
        "mx": [{"size":0,"price":"40","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":100001,"sizeid":0}],
        }
    udata = {"unlisted":False, "ds_cat_rcmd_id":""}
    udata["logistics_channels"] = chs[site]
    ks = ["id", "name", "brand", "images", "description", "model_list", 
    "category_path", "attribute_model", "parent_sku", "wholesale_list", 
    "installment_tenures", "weight", "dimension", "pre_order", 
    "days_to_ship", "condition", "size_chart", "video_list", 
    "video_task_id", "tier_variation", "add_on_deal", "price",
    "stock", "category_recommend",]
    for k in ks:
        udata[k] = data[k]
    
    if len(udata['model_list']) == 0:
        udata['stock'] = stock
    else:
        nms = [];
        for  m in udata['model_list']:
            if m['id'] == model_id:
                udata['stock'] += stock - m['stock']
                m['stock'] = stock
            nm = {}
            mks = ["id", "is_default","name", "sku", "stock","tier_index"]
            for mk in mks:
                nm[mk] = m[mk]
            nms.append(nm)
        udata['model_list'] = nms

    updata = [udata,]
    uurl = host(site) + "/api/v3/product/update_product"
    params = "/?version=3.1.0&SPC_CDS_VER=2&SPC_CDS=" + cookies['SPC_CDS']
    res = requests.post(uurl + params, json=updata, cookies=cookies)
    #print(udata)
    print(item_id, res.json(), res.status_code)
    return res.json()
   
def update_listing_backup(account, cookies, item_id, model_id, stock):    
    cookies = get_cookie_jar(account)
    site = account[-2:]
    url = host(site) + "/api/v3/product/get_product_detail"
    params = "/?SPC_CDS_VER=2&product_id=" + str(item_id)
    res = requests.get(url + params, cookies=cookies)
    data = res.json()['data']
    #print(data)
    chs = {
        "my": [{"size":0,"price":"5.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":28016,"sizeid":0}],
        "id": [{"size":0,"price":"10000.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":88001,"sizeid":0}],
        "th": [{"size":0,"price":"20","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":78004,"sizeid":0}],
        "ph": [{"size":0,"price":"40","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":48002,"sizeid":0}],
        "vn": [{"size":0,"price":"10000","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":58007,"sizeid":0}],
        "sg": [{"size":0.02,"price":"0.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18028,"sizeid":0}],
        "br": [{"size":0,"price":"15","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":90001,"sizeid":0}],
        "mx": [{"size":0,"price":"40","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":100001,"sizeid":0}],
        }
    udata = {"unlisted":False, "ds_cat_rcmd_id":""}
    udata["logistics_channels"] = chs[site]
    ks = ["id", "name", "brand", "images", "description", "model_list", 
    "category_path", "attribute_model", "parent_sku", "wholesale_list", 
    "installment_tenures", "weight", "dimension", "pre_order", 
    "days_to_ship", "condition", "size_chart", "video_list", 
    "video_task_id", "tier_variation", "add_on_deal", "price",
    "stock", "category_recommend",]
    for k in ks:
        udata[k] = data[k]
    
    if len(udata['model_list']) == 0:
        udata['stock'] = stock
    else:
        nms = [];
        for  m in udata['model_list']:
            if m['id'] == model_id:
                udata['stock'] += stock - m['stock']
                m['stock'] = stock
            sku = mydb('select model_sku from items where model_id=?',[m["id"],])[0][0]
            m["sku"] = sku
            nm = {}
            mks = ["id", "is_default","name", "sku", "stock","tier_index"]
            for mk in mks:
                nm[mk] = m[mk]
            nms.append(nm)
        udata['model_list'] = nms

    updata = [udata,]
    uurl = host(site) + "/api/v3/product/update_product"
    params = "/?version=3.1.0&SPC_CDS_VER=2&SPC_CDS=" + cookies['SPC_CDS']
    res = requests.post(uurl + params, json=updata, cookies=cookies)
    #print(udata)
    print(item_id, res.json(), res.status_code)
    return res.json()

def update_promotion_price(account, cookies, itemid, modelid, price):
    site = account[-2:]
    itemid, modelid, price = int(itemid), int(modelid), float(price)
    url = host(site) + "/api/v3/product/get_product_detail"
    params = "/?SPC_CDS_VER=2&product_id=" + str(itemid)
    res = requests.get(url + params, cookies=cookies)
    data = res.json()['data']
    for m in data['model_list']:
        if m['id'] == modelid:
            discount_id = m['promotion_id']
            break
    #print(data, modelid)
    url = host(site) + "/api/marketing/v3/discount/nominate/"
    url += "?SPC_CDS_VER=2&SPC_CDS=" + cookies["SPC_CDS"]
    data = {
    "discount_id": discount_id,
    "discount_model_list":[{
    "itemid": itemid,
    "modelid": modelid,
    "promotion_price": price,
    "user_item_limit":0,
    "status":1
    }]
    }
    res = requests.put(url, json=data, cookies=cookies)
    print(itemid, modelid, res.json())

def ad_account(account, report):
    #check_cookie_jar(account)
    cookies = get_cookie_jar(account)
    url = host(account[-2:]) + '/api/marketing/v3/pas/report/shop_report_by_time/'
    h, m, s = time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_sec
    end = int(time.time()) - (h * 60 + m) * 60 - s
    start = end - 60 *60 *24 * 7
    params = {
    'start_time': start,
    'end_time': end,
    'placement_list': '[0,4]',
    'agg_interval': 12,
    'SPC_CDS_VER': 2,
    'SPC_CDS': cookies['SPC_CDS']
    }
    mp = {'account': account}
    mp['start'], mp['end'] = snow(start), snow(end)
    rs = requests.get(url, params=params, cookies=cookies)
    data = rs.json()
    assert data['message'] == 'success', data['message']
    keys = ['impression','click','cost','order','order_gmv']
    for k in keys:
        mp[k] = sum([float(i[k]) for i in data['data']])
    #print(mp)

    url = host(account[-2:]) + '/api/marketing/v3/pas/account/?SPC_CDS_VER=2&SPC_CDS=' + cookies['SPC_CDS']
    rs = requests.get(url, cookies=cookies)
    mp['balance'] = float(rs.json()['data']['balance'])
    print(mp)
    keys = ['start', 'end', 'account', 'balance', 'impression','click','cost','order','order_gmv']
    rs = [mp[i] for i in keys]
    report.append(rs)
    return rs

def ad_report():
    con = mydb('select account from password')
    account_list = [i[0] for i in con]
    report = []
    values = [[i, report] for i in account_list]
    multiple_mission_pool(ad_account,  values)
    print(report)
    sql = 'insert into ad values(?,?,?,?,?,?,?,?,?)'
    mydb('delete from ad')
    mydb(sql, report, True)

if __name__ == '__main__':
    #ad_report()
    pass