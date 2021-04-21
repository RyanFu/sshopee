#coding=utf-8  
import sqlite3, json, os, requests, time, csv, zipfile, pprint
from api_tools import *
from shopee_api import *
from app import *
from bs4 import BeautifulSoup

def file_process():
    root_path = r"C:\Users\guoliang\Downloads\2月"
    for fo in os.listdir(root_path):
        fop = "\\".join([root_path, fo])
        for f in os.listdir(fop):
            nf = fo + "." + f
            f = "\\".join([fop, f])
            nf = "\\".join([fop, nf])
            print(f, nf)
            os.rename(f, nf)

def erp2zong_page(sku_list):
    sku_list = ",".join(sku_list)
    ev = '''<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
        <GetProducts xmlns="http://tempuri.org/">
        <productRequest>
        <CustomerID>1551</CustomerID>
        <UserName>guoliang</UserName>
        <Password>gl23r42</Password>
        <ClientSKUs>{sku_list}</ClientSKUs>
        </productRequest>
        </GetProducts>
        </soap:Body>
        </soap:Envelope>'''.format(sku_list=sku_list)

    headers = {"content-type" : "text/xml; charset=utf-8"}
    url = "http://runbu.irobotbox.com/Api/API_ProductInfoManage.asmx"
    res = requests.post(url, data=ev, headers=headers)
    sp = BeautifulSoup(res.text, 'xml')
    rs = sp("ApiProductInfo")
    data = []
    ks = ('ClientSKU', 'ProductName', 'ProductNameCN', 'WithBattery', 'ProductState', 
    'LastSupplierPrice', 'GrossWeight', 'GoodNum', 'AvgDailySales')
    for row in rs:
        #print(row)
        vs = [row.find(k).getText() for k in ks]
        data.append(vs)
    sql  = 'insert into song values(?,?,?,?,?,?,?,?,?)'
    mydb(sql, data, many=True)
        
def erp2zong():
    mydb("delete from song;")
    con = mydb("select sku from zong ")
    sku_list = [i[0] for i in con]
    data = []
    for i in range(0, len(sku_list), 50):
        cur_list = sku_list[i: i + 50]
        data.append((cur_list,))
    multiple_mission_pool(erp2zong_page, data)
    return

def readcats(cats):
    t1 = snow()
    ch_options = Options()
    ch_options.add_argument("--headless")
    ch_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=driver_path, options=ch_options)
    for cat in cats:
        url = 'https://ph.xiapibuy.com/search'
        params = '?locations=-2&noCorrection=true&page=0&subcategory=' + str(cat)
        driver.get(url + params)
        WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_class_name("shopee-search-item-result__item"))
        for i in range(6):
            driver.execute_script("window.scrollBy(0,400)")
            time.sleep(0.5)
        items = driver.find_elements_by_class_name("shopee-search-item-result__item")
        rows = []
        for i in items:
            try:
                img = i.find_element_by_tag_name('img').get_attribute('src')[:-3]
                link = i.find_element_by_tag_name('a').get_attribute('href')
                name = link.split("com/")[1].split(" i.")[0].replace("-", " ")
                rows.append([img, link, cat, name])
                print(cat, len(rows))
            except:
                print(cat, 'missing')
        sql = 'insert or replace into temp values(?,?,?,?)'
        mydb(sql, rows, True)
    driver.quit()
    t2 = snow()
    print(t1, t2)

def catformate(site):
    check_cookie_jar('elenxs.' + site)
    step = 300
    find = 0
    for i in range(0, 150000, step):   
        sql = "select distinct name, category_id from items where account like '%.{}' limit ? offset ?".format(site)
        con = mydb(sql, (step, i))
        names = [i[0] for i in con]
        if len(names) == 0:
            break
        mp = shopee_recommend_category(names, 'elenxs.my')
        data = [[mp[name], name, cat] for name, cat in con if int(mp[name]) > 0]
        sql = "update items set model_name = ? where name = ? and category_id = ?"
        mydb(sql, data, True)
        find += len(data)
        print(i + step, find, round(find/(i + step), 2))
        if len(data) == 0:
            print('over speed')
            for i in range(5):
                time.sleep(1)
                print('waiting')

#获取账号全部订单
def get_orders_by_account(account):
    site = account.split(".")[1]
    cookies = get_cookie_jar(account) 
    url = host(site) + '/api/v3/order/get_order_id_list'
    params = {
    'SPC_CDS_VER':2,
    'sort_by':'create_date_desc',
    'page_size':10,
    'page_number':2,
    'from_page_number':1,
    'total':0,
    'flip_direction':'ahead',
    }
    data = requests.get(url, params=params,cookies=cookies, headers=headers).json()
    orders = data['data']['orders'] #shop_id,order_id
    order_ids = [str(i['order_id']) for i in orders]
    order_ids = ','.join(order_ids)
    print(account, len(orders), order_ids)
    url = host(site) + '/api/v3/order/get_compact_order_list_by_order_ids'
    params = {'SPC_CDS_VER':2, 'order_ids':order_ids}
    data = data = requests.get(url, params=params,cookies=cookies, headers=headers).json()
    orders = data['data']['orders'] 
    print(account, len(orders))
    #assert 0
    values = []
    for r in orders:
        order_sn = r['order_sn']
        payby_date = snow(r['payby_date'])
        print(len(r['order_items']))
        for i in r['order_items']:
            item_id = i['item_model']['item_id']
            model_id = i['item_model']['model_id']
            ctime = snow(i['item_model']['ctime'])
            row = [account, order_sn, payby_date, item_id, model_id, ctime]
            values.append(row)
    sql = '''insert into orders values (?, ?, ?, ?, ?, ?)'''
    mydb(sql, values, True)
    return

def follow_one(site, cookies, shop_id):
    url = host(site) +  '/api/v3/settings/follow_shop/?SPC_CDS_VER=2&SPC_CDS=' + cookies['SPC_CDS']
    data = {'is_follow': True, 'target_shop_id': shop_id}
    re = requests.post(url, json=data, headers=headers, cookies=cookies)
    print(shop_id, re.text)

def auto_follow(account):
    site = account[-2:]
    check_cookie_jar(account)
    cookies = get_cookie_jar(account)
    con = mydb('select shopid from shopids where site = ? order by used asc limit 300', [site,])
    ids = [i[0] for i in con]
    values = [[site, cookies, shop_id] for shop_id in ids]
    multiple_mission_pool(follow_one, values)
    mydb('update shopids set used = used + 1 where shopid = ?', con, True)

account = 'bigbighouse.my'
auto_follow(account)
