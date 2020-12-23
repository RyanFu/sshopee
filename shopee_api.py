#coding=utf-8  
import sqlite3, json, requests, time, threading
import selenium_chrome

database_name = "./shopee.db" 
ua = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"

def multiple_mission(func, args_list, interval=1):    
    mission_list = []
    for args in args_list:
        mission = threading.Thread(target=func, args = args)
        mission_list.append(mission)
    for mission in mission_list:
        mission.start()
        time.sleep(interval)
    return

def check_cookie_jar(account):
    with  sqlite3.connect(database_name) as cc:
        sql = "select cookies from cookies where account = ?"
        cu = cc.execute(sql, [account])
        con = cu.fetchone()

    if con is not None:
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

    if con is None or message != "success":
        print(account, " cookies invalid, update now")
        with  sqlite3.connect(database_name) as cc:
            sql = "select password from password where account = ?"
            cu = cc.execute(sql, [account])
            con = cu.fetchone()
            password = con[0]
        selenium_chrome.open_sellercenter(account, password, "1")

    return

def get_cookie_jar(account):
    with  sqlite3.connect(database_name) as cc:
        sql = "select cookies from cookies where account = ?"
        cu = cc.execute(sql, [account])
        con = cu.fetchone()
    cookie_dict = json.loads(con[0])
    cookie_jar = requests.utils.cookiejar_from_dict(cookie_dict)
    return cookie_jar

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
        url = "https://seller.{site}.shopee.cn/api/v2/shops/performance".format(site=site)
        data = se.get(url).json()
        values = [
            account,
            follower_count,
            item_count,
            data["overall_review_rating"]["my"],
            rating_count,
            data["pre_order_listing_rate"]["my"] + "%",
            "",
            data["response_rate"]["my"] + "%",
            data["non_fulfilment_rate"]["my"] + "%",
            data["cancelation_rate"]["my"] + "%",
            data["return_refund_rate"]["my"] + "%",
            round(data["average_preparation_time"]["my"]/3600/24, 2),
            data["late_shipment_rate"]["my"] + "%"
        ]
        print(values)
        return values

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

def get_single_page(account, page_num, dp=False):
    site = account.split(".")[1]
    host = "https://seller.{site}.shopee.cn".format(site=site)    
    url = host + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=48&version=3.2.0&page_number={num}".format(num=page_num)
    with requests.Session() as se:
        se.cookies = get_cookie_jar(account)
        se.headers.update({'User-Agent': ua})
        data = se.get(url+params).json()
        print(data["message"])
        total_count = data["data"]["page_info"]["total"]
        page = data["data"]["list"]
        row_list = convert_page_list(page)
        for row in row_list:
            row.append(account)
            row.append(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
        data = {"account": account, "rows": row_list}
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        se.post("http://localhost:5000/shopee_add_items", json=data, headers=headers)

        conplete_count = page_num * 48
        if conplete_count <= total_count:
            print("complete listng count ", conplete_count)
            if dp:
                get_single_page(account, page_num + 1)


def get_all_page(account):
    site = account.split(".")[1]
    host = "https://seller.{site}.shopee.cn".format(site=site)    
    url = host + "/api/v3/product/page_product_list"
    params = "/?source=seller_center&page_size=12&version=3.2.0&page_number=1"
    with requests.Session() as se:
        se.cookies = get_cookie_jar(account)
        se.headers.update({'User-Agent': ua})
        data = se.get(url+params).json()
        message = data["message"]
        total_count = data["data"]["page_info"]["total"]
    total_page = total_count // 48 + 1
    num_list = [[account, i + 1,] for i in range(total_page)]
    multiple_mission(get_single_page, num_list)