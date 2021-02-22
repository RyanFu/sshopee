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

def logit(logfile='out.log'):
    def logging_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            log_string = func.__name__ + " was called"
            print(log_string)
            # 打开logfile，并写入内容
            with open(logfile, 'a') as opened_file:
                # 现在将日志打到指定的logfile
                opened_file.write(log_string + '\n')
            return func(*args, **kwargs)
        return wrapped_function
    return logging_decorator



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
    
# def update_stock_listing(account, cookies, item_id, model_id, stock):    
    # cookies = get_cookie_jar(account)
    # site = account[-2:]
    # host = "https://seller.{}.shopee.cn".format(site)
    # url = host + "/api/v3/product/get_product_detail"
    # params = "/?SPC_CDS_VER=2&product_id=" + str(item_id)
    # res = requests.get(url + params, cookies=cookies)
    # data = res.json()['data']
    # #print(data)
    # chs = {
        # "my": [{"size":0,"price":"5.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":28016,"sizeid":0}],
        # "id": [{"size":0,"price":"10000.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":88001,"sizeid":0}],
        # "th": [{"size":0,"price":"20","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":78804,"sizeid":0}],
        # "ph": [{"size":0,"price":"40","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":48802,"sizeid":0}],
        # "vn": [{"size":0,"price":"10000","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":58007,"sizeid":0}],
        # "sg": [{"size":0.02,"price":"0.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18028,"sizeid":0}],
        # "br": [{"size":0,"price":"15","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":90001,"sizeid":0}],
        # }
    # udata = {"unlisted":False, "ds_cat_rcmd_id":""}
    # udata["logistics_channels"] = chs[site]
    # ks = ["id", "name", "brand", "images", "description", "model_list", 
    # "category_path", "attribute_model", "parent_sku", "wholesale_list", 
    # "installment_tenures", "weight", "dimension", "pre_order", 
    # "days_to_ship", "condition", "size_chart", "video_list", 
    # "video_task_id", "tier_variation", "add_on_deal", "price",
    # "stock", "category_recommend",]
    # for k in ks:
        # udata[k] = data[k]
    
    # if len(udata['model_list']) == 0:
        # udata['stock'] = stock
    # else:
        # nms = [];
        # for  m in udata['model_list']:
            # if m['id'] == model_id:
                # udata['stock'] += stock - m['stock']
                # m['stock'] = stock
            # nm = {}
            # mks = ["id", "is_default","name", "sku", "stock","tier_index"]
            # for mk in mks:
                # nm[mk] = m[mk]
            # nms.append(nm)
        # udata['model_list'] = nms

    # updata = [udata,]
    # uurl = host + "/api/v3/product/update_product"
    # params = "/?version=3.1.0&SPC_CDS_VER=2&SPC_CDS=" + cookies['SPC_CDS']
    # res = requests.post(uurl + params, json=updata, cookies=cookies)
    # #print(udata)
    # print(res.json(), res.status_code)
    # return res.json()

def update_stock_account(account, rows):
    check_cookie_jar(account)
    cookies = get_cookie_jar(account)
    values = [[account, cookies, *i] for i in rows]
    multiple_mission_pool(update_stock_listing, values)
account = 'jihuishi.vn'
rows = [[4548971823,30767917234,21]]
#rows[0] = [str(i) for i in rows[0]]
update_stock_account(account, rows)

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

def auto_upload_stock():
    account_list = ['jihuishi.my','jihuishi.id','jihuishi.th','jihuishi.ph','jihuishi.vn','jihuishi.sg']
    account_list = ['machinehome.my','machinehome.id','machinehome.th','machinehome.ph','machinehome.vn','machinehome.sg']
    for account in account_list:
        account, password = mydb('select account, password from password where account=?', (account,))[0]
        upload_stock(account, password)


def get_recommend_category_one(name, site, cookies, mp):
    host = "https://seller.my.shopee.cn"
    url = host + "/api/v3/category/get_recommend_category".replace("my", site)
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

def get_recommend_category(name_list, account):
    cookies = get_cookie_jar(account)
    site = account[-2:]
    mp = {}
    values = [[i, site, cookies, mp] for i in name_list]
    multiple_mission_pool(get_recommend_category_one, values)
    #result = [mp[i] for i in name_list]
    #print(result)
    return mp


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






