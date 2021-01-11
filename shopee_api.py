#coding=utf-8  
import sqlite3, json, requests, time, threading, platform
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

db_lock = threading.Lock();
if platform.system() == "Windows":
    database_name = "D:/shopee.db"
    driver_path = 'D:/chromedriver_win32/chromedriver.exe'
else:
    database_name = "/root/shopee.db"
    driver_path = "/root/chromedriver.exe"
ua = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"
#http://chromedriver.storage.googleapis.com/index.html

#多线程任务封装
def multiple_mission(func, args_list, max_number=5):
    num = len(args_list)
    print('total mission number is ', num)
    for i in range(num):
        args = args_list[i]
        while threading.active_count() > max_number + 1:
            print('reach max mission number, waiting...')
            time.sleep(1)
        mission = threading.Thread(target=func, args = args)
        mission.start()
        print('start mission NO.', i)
    return

#使用SELENIUM控制CHORME打开账号后台
def open_sellercenter(account, password, cookie_only):
    print(account, password)
    site = account[-2:]
    ch_options = Options()
    if cookie_only == "1":
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
        cc.execute(sql, [account, cookies_text, time.ctime()])
        cc.commit()
    return cookies_text

#检查COOKIES有效性,失效则更新
def check_cookie_jar(account):
    with  sqlite3.connect(database_name) as cc:
        sql = "select cookies from cookies where account = ?"
        cu = cc.execute(sql, [account])
        con = cu.fetchone()
    if con is None:
        print(account, ' cookies not found, go get it now')
    else:
        cookie_dict = json.loads(con[0])
        cookie_jar = requests.utils.cookiejar_from_dict(cookie_dict)
        site = account.split(".")[1]
        host = "https://seller.{site}.shopee.cn".format(site=site)    
        url = host + "/api/v3/product/page_product_list"
        params = "/?source=seller_center&page_size=12&version=3.2.0&page_number=1"
        with requests.Session() as se:
            se.cookies = cookie_jar
            se.headers.update({'User-Agent': ua})
            data = se.get(url+params).json()
            message = data["message"]
        if message != "success":
            print(account, " cookies invalid, update now")
            con = None

    if con is None:       
        with  sqlite3.connect(database_name) as cc:
            sql = "select password from password where account = ?"
            cu = cc.execute(sql, [account])
            con = cu.fetchone()
            password = con[0]
        selenium_chrome.open_sellercenter(account, password, True)
    print(account, ' cookies updated')
    return

#获取账号COOKIES
def get_cookie_jar(account):
    with  sqlite3.connect(database_name) as cc:
        sql = "select cookies from cookies where account = ?"
        cu = cc.execute(sql, [account])
        con = cu.fetchone()
    cookie_dict = json.loads(con[0])
    cookie_jar = requests.utils.cookiejar_from_dict(cookie_dict)
    return cookie_jar

#插入前先清空账号避免重复
def clear_listing(account):
    with  sqlite3.connect(database_name) as cc:
        sql = "delete from items where account = ?"
        cu = cc.execute(sql, [account])
    return

def get_performance(account):
    site = account.split(".")[1]
    with requests.Session() as se:
        se.cookies = get_cookie_jar(account)
        se.headers.update({'User-Agent': ua})
        url = "https://seller.{site}.shopee.cn/api/v3/general/get_shop".format(site=site)
        data = se.get(url).json()["data"]
        follower_count = data["follower_count"]
        item_count = data["item_count"]
        rating_count = data["rating_bad"] + data["rating_good"] + data["rating_normal"]
        url = "https://seller.{site}.shopee.cn/api/v2/shops/sellerCenter/ongoingPoints".format(site=site)
        data = se.get(url).json()["data"]
        totalPoints = data["totalPoints"]
        url = "https://seller.{site}.shopee.cn/api/v2/shops/sellerCenter/shopPerformance".format(site=site)
        data = se.get(url).json()
        data = data["data"]
        print(data)
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
        #values = [float(i) for i in values]
        print(values)
        return values

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
def get_single_page(account, cookie_jar, page_num, dp=False):
    site = account.split(".")[1]
    host = "https://seller.{site}.shopee.cn".format(site=site)    
    url = host + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=48&version=3.2.0&page_number={num}".format(num=page_num)
    with requests.Session() as se:
        se.cookies = cookie_jar
        se.headers.update({'User-Agent': ua})
        data = se.get(url+params).json()
        print(data["message"])
        total_count = data["data"]["page_info"]["total"]
        page = data["data"]["list"]
        row_list = convert_page_list(page)
        for row in row_list:
            row.append(account)
            row.append(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        rows = row_list[1:]
        sql = "insert into items values (?" + ",?" * 24 + ")"
        rows2delete = [[i[0], i[16]] for i in rows]
        sql2delete = "delete from items where item_id=? and model_id=?"
        with db_lock:
            with sqlite3.connect(database_name) as cc:
                cc.executemany(sql2delete, rows2delete)
                cc.executemany(sql, rows)
                cc.commit()
        print(time.ctime(), account, "add items complete")

        conplete_count = page_num * 48
        if conplete_count <= total_count:
            print("complete listng count ", conplete_count)

#更新账号全部产品
def get_all_page(account):
    site = account.split(".")[1]
    cookie_jar = get_cookie_jar(account)  
    host = "https://seller.{site}.shopee.cn".format(site=site)
    url = host + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=12&version=3.2.0&page_number=1"
    with requests.Session() as se:
        se.cookies = cookie_jar
        se.headers.update({'User-Agent': ua})
        data = se.get(url+params).json()
        message = data["message"]
        total_count = data["data"]["page_info"]["total"]
    total_page = total_count // 48 + 1
    num_list = [[account, cookie_jar, i] for i in range(1, total_page + 1)]
    multiple_mission(get_single_page, num_list)
