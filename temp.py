#coding=utf-8  
import sqlite3, json, os, requests, time, csv
from machine_gun import *
from shopee_api import *
from bs4 import BeautifulSoup
def file_process():
    root_path = r"C:\Users\guoliang\Downloads\1月"
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

def upload_stock(account, password, silent=True):
    site = account[-2:]
    file_path = 'D:/Downloads/2restock_{}.xlsx'.format(account)
    ch_options = Options()
    if silent:
        ch_options.add_argument("--headless")
        ch_options.add_argument("--no-sandbox")
    t1 = snow()
    driver = webdriver.Chrome(executable_path=driver_path, options=ch_options)
    driver.get('https://seller.{site}.shopee.cn/account/signin'.format(site=site))
    print("find login page", snow())
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_tag_name("input"))
    bs = driver.find_elements_by_tag_name('input')
    bs[0].send_keys(account)
    bs[1].send_keys(password)
    driver.find_element_by_tag_name('button').click()
    print("login done", snow())
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_class_name("num"))
    driver.get('https://seller.{site}.shopee.cn/portal/tools/mass-update/upload'.format(site=site))
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_class_name('shopee-upload__input'))
    driver.find_element_by_class_name('shopee-upload__input').send_keys(file_path)
    print('upload done', t1, snow())
    time.sleep(5)
    driver.quit()


cats = [19074,19073,19072,19071,19070,19069,20327,19068,6965,17274]
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
        for i in range(5):
            driver.execute_script("window.scrollBy(0,500)")
        items = driver.find_elements_by_class_name("shopee-search-item-result__item")
        rows = []
        for i in items:
            try:
                img = i.find_element_by_tag_name('img').get_attribute('src')[:-3]
                link = i.find_element_by_tag_name('a').get_attribute('href')
                rows.append([img, link, cat])
                print(cat, len(rows))
            except:
                print(cat, 'missing')
        sql = 'insert or replace into temp values(?,?,?)'
        mydb(sql, rows, True)
    driver.quit()
    t2 = snow()
    print(t1, t2)


def update_promotion_price(account, cookies, itemid, modelid, price):
    site = account[-2:]
    url = host(site) + "/api/v3/product/get_product_detail"
    params = "/?SPC_CDS_VER=2&product_id=" + str(itemid)
    res = requests.get(url + params, cookies=cookies)
    data = res.json()['data']
    for m in data['model_list']:
        if m['id'] == modelid:
            discount_id = m['promotion_id']
            break
    #print(data)
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


check_cookie_jar(account)
cookies = get_cookie_jar(account)
values = [[account, cookies, *i] for i in rows]
multiple_mission_pool(update_promotion_price, values, debug=True)


