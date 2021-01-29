#coding=utf-8  
#import gevent
import sqlite3, json, requests, time, platform
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from machine_gun import multiple_mission_pool, decor_retry, decor_async, snow, db_lock

if platform.system() == "Windows":
    database_name = "D:/shopee.db"
    driver_path = 'D:/chromedriver_win32/chromedriver.exe'
else:
    database_name = "/root/shopee.db"
    driver_path = "/root/chromedriver.exe"
ua = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"
headers = {'User-Agent': ua}
#http://chromedriver.storage.googleapis.com/index.html

def mydb(sql, values=(), many=False):
    with sqlite3.connect(database_name) as db:
        if 'select' in sql:
            cur = db.execute(sql, values)
            rv = cur.fetchall()
        else:
            with db_lock:
                if many:
                    db.executemany(sql, values)
                else:
                    db.execute(sql, values)
                db.commit()
            rv = None
    return rv

#使用SELENIUM控制CHORME打开账号后台
def open_sellercenter(account, password, cookie_only):
    print(account, password)
    site = account[-2:]
    ch_options = Options()
    if cookie_only:
        ch_options.add_argument("--headless")
        ch_options.add_argument("--no-sandbox")
        print("no head")

    driver = webdriver.Chrome(executable_path=driver_path, options=ch_options)
    driver.get('https://seller.{site}.shopee.cn/account/signin'.format(site=site))
    print("find login page")
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_tag_name("input"))
    bs = driver.find_elements_by_tag_name('input')
    bs[0].send_keys(account)
    bs[1].send_keys(password)
    driver.find_element_by_tag_name('button').click()
    print("login done")
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_class_name("num"))
    cookies_raw = driver.get_cookies()
    if cookie_only:  
        driver.quit()

    cookies_dict = {}
    for i in cookies_raw:
        k = i["name"]
        v = i["value"]
        cookies_dict[k] = v

    cookies_text = json.dumps(cookies_dict)
    with  sqlite3.connect(database_name) as cc:
        sql = "insert or replace into cookies values(?, ?, ?)"
        t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cc.execute(sql, [account, cookies_text, t])
        cc.commit()
    return cookies_text

#检查COOKIES有效性,失效则更新
def check_cookie_jar(account):
    sql = "select cookies from cookies where account = ?"
    con = mydb(sql, [account])        
    if con:
        cookie_dict = json.loads(con[0][0])
        site = account.split(".")[1]
        host = "https://seller.{site}.shopee.cn".format(site=site)    
        url = host + "/api/v3/product/page_product_list"
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
    return cookie_jar


def get_performance(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account)
    url = "https://seller.{site}.shopee.cn/api/v3/general/get_shop".format(site=site)
    data = requests.get(url, cookies=cookies, headers=headers).json()["data"]
    follower_count = data["follower_count"]
    item_count = data["item_count"]
    rating_count = data["rating_bad"] + data["rating_good"] + data["rating_normal"]
    url = "https://seller.{site}.shopee.cn/api/v2/shops/sellerCenter/ongoingPoints".format(site=site)
    data = requests.get(url, cookies=cookies, headers=headers).json()["data"]
    totalPoints = data["totalPoints"]
    url = "https://seller.{site}.shopee.cn/api/v2/shops/sellerCenter/shopPerformance".format(site=site)
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
    cu = mydb(sql)
    account_list = [i for i in cu]
    multiple_mission_pool(get_performance, account_list, 10)
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
    host = "https://seller.{site}.shopee.cn".format(site=site)    
    url = host + "/api/v3/product/page_product_list"
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
    host = "https://seller.{site}.shopee.cn".format(site=site)
    url = host + "/api/v3/product/page_product_list"
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
def tm_get_all_page(account):
    get_all_page(account)
    return
    

@decor_async
def mytimer():
    while True:        
        h = time.localtime().tm_hour
        if h == 0:
            print(time.ctime(), "do it now")
            cu = mydb('select account from password')
            account_list = [i[0] for i in cu]
            for account in account_list:
                check_cookie_jar(account)
                tm_get_all_page(account)
                time.sleep(60*3)
        else:
            print(time.time(), "waiting...")
        time.sleep(60*60)
 
    
#获取取消订单
def get_cancellations_by_account(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account) 
    url = 'https://seller.{}.shopee.cn/api/v3/order/get_simple_order_ids'.format(site)
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
    url = 'https://seller.{}.shopee.cn/api/v3/order/get_compact_order_list_by_order_ids'.format(site)
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
      
def cancellation_reject_accept():
    url = 'https://seller.br.shopee.cn/api/v3/order/respond_cancel_request'
    params = {'order_id':'', 'action': 'accept'}

def get_returns_by_account(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account) 
    url = 'https://seller.{}.shopee.cn/api/v1/return/list'.format(site)
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