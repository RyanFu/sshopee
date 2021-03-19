#coding=utf-8  
import sqlite3, json, os, requests, time, csv, zipfile
from api_tools import *
from shopee_api import *
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
    con = mydb("select sku from stock where stock > 0 ")
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

def ad_account(account):
    host = host(account[-2:])
    cookies = get_cookie_jar(account)
    url = host + '/api/marketing/v3/pas/report/shop_report_by_time/'
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

    url = host + '/api/marketing/v3/pas/account/?SPC_CDS_VER=2&SPC_CDS=' + cookies['SPC_CDS']
    rs = requests.get(url, cookies=cookies)
    mp['balance'] = float(rs.json()['data']['balance'])
    print(mp)
    keys = ['start', 'end', 'account', 'balance', 'impression','click','cost','order','order_gmv']
    rs = [mp[i] for i in keys]
    return rs

print(ad_account('machinehome.ph'))