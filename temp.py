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
    
def update_stock():
    account, item_id, model_id, stock = "jihuishi.sg", 9309705353,73333353757, 80
    con = mydb('select cookies from cookies where account = ?', (account,))
    cookies = json.loads(con[0][0])
    site = account[-2:]
    host = "https://seller.{}.shopee.cn".format(site)
    url = host + "/api/v3/product/get_product_detail"
    params = "/?SPC_CDS_VER=2&product_id=" + str(item_id)
    res = requests.get(url + params, cookies=cookies)
    data = res.json()['data']

    mych = [{"size":0,"price":"5.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":28016,"sizeid":0}]
    idch = [{"size":0,"price":"10000.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":88001,"sizeid":0}]
    sgch = [{"size":0.02,"price":"0.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18028,"sizeid":0},
    {"size":0.02,"price":"1.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18025,"sizeid":0}]
    udata = {"unlisted":False, "ds_cat_rcmd_id":"", "video_list":[],"video_task_id":None}
    udata["logistics_channels"] = sgch
    ks = ["id","name","brand","images","description","model_list","category_path","attribute_model",
          "category_recommend","stock","price","parent_sku","wholesale_list",
          "installment_tenures","weight","dimension","pre_order","days_to_ship","condition","size_chart",
          "tier_variation","add_on_deal"]
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
            mks = ["id", "name", "price", "sku", "stock", "tier_index"]
            for mk in mks:
                nm[mk] = m[mk]
            nms.append(nm)
        udata['model_list'] = nms

    # updata = [udata,];
    # uurl = host + "/api/v3/product/update_product/?version=3.1.0&SPC_CDS_VER=2"
    # res = requests.post(uurl, json=updata, cookies=cookies)
    # print(uurl, "\n".join(udata.keys()))
    # print(res.json())
    a = {"id":9309705353,"name":"Multifunctional Android Phones Mobile Phone External Infrared Thermal Imager Adapter Included_jihuishi","brand":"","images":["dd5ed2a1bb43aa0d4e5f6a28f03f4091","9c00b5101fc1084ce50fe7df0a516b2b","f261138d0dcfb13a663335b626fb489e","45d5325a962651a51cf1053a051e164d","434ca17c9d623540af03ff7e0c3989f9","3e03b0814c31755ecfd802dee316c2ab","fdb3038a7661ef125b0b673b115c0f05","3d21bf79214b3a33477e7e060159dec1","3f4c20ee7c0a4a9d3b7c231602efc497"],"description":"Description:\r\nYou can use this phone thermal imager during day and night and capture image of hot item within a certain distance.\r\nJust insert this Infrared thermal imager into your phone and the software will open automatically,is convenient to use.\r\nCome with a type-c adapter for you to use this phone thermal camera on phones that don't support type-c port.\r\nThis phone thermal imager is durable and can be used for a long time with a storage box,you can safely carry this around.\r\nThis Android phone thermal camera has many funcations,such as center point temperature display,point temperature measurement,image fusion,mirroring,temperature unit setting,palette setting face detection photo shooting,video recording.\r\n\r\nSpecification:\r\nMaterial: metal.\r\nColor: Black.\r\nSize: 60*30mm.\r\nTemperature range: -20 ℃ to 300 ℃ \r\nAccuracy: ± 3 ℃ or ± 5% of reading \r\nResolution: 0.1 ℃ or 0.1 ℉ \r\nWorking band: 8-14μm \r\nHorizontal viewing angle: ° ± 1 ° / 43 ° ± 1 ° \r\nInfrared resolution image: 32 * 32 \r\nVisible Image Resolution: 640 * 480 \r\nImage format: PNG \r\nVideo format: mP4 \r\nFrame rate: gHz \r\nFocal length: fixed \r\nOperation temperature range: 0 ℃ to 35 ℃ \r\nStorage temperature range: -20 ℃ to 60 ℃ \r\nPlug: USB Type-C \r\nPower supply: power supply from external devices \r\n\r\nNote\r\nThere might be a bit color distortions due to different computer resolutions.\r\nThere might be a slight errors due to different hand measurement.\r\nThe phone USB must support OTG function.\r\nThe phone must support UVC camera.\r\nThe phone must support OS for Android 4.3 or above.\r\n\r\nPackage included:\r\n1* Infrared thermal imager.\r\n1* Adapter.\r\n1* Storage Box.\r\n1* User manual.\r\n\r\nWelcome to Jihuishi\r\n\nPlease read the product description before ordering\r\n\nIt usually takes 8-14 days by sea.\nIf you have any questions\r\n please contact us.\nThank you. Have a nice day","model_list":[{"id":73333353757,"sku":"","tier_index":[0],"is_default":True,"name":"Multifunctional Android Phones Mobile Phone External Infrared Thermal Imager Adapter Included_jihuishi","item_price":"","stock":200}],"category_path":[8,2313,10956],"attribute_model":{"attribute_model_id":11510,"attributes":[{"status":1,"attribute_id":461,"value":"No Brand"},{"status":2,"attribute_id":10100,"value":""},{"status":2,"attribute_id":10101,"value":""}]},"parent_sku":"GJ2844-00B","wholesale_list":[],"installment_tenures":{"status":0,"enables":[],"tip_type":0},"weight":"0.22","dimension":{"width":0,"height":0,"length":0},"pre_order":False,"days_to_ship":2,"condition":1,"size_chart":"","video_list":[],"video_task_id":"","tier_variation":[{"name":"","options":[""],"images":[]}],"add_on_deal":[],"price":"210.40","stock":200,"logistics_channels":[{"size":0,"price":"1.00","cover_shipping_fee":False,"enabled":True,"item_flag":"0","channelid":18025,"sizeid":0},{"size":0,"price":"0.00","cover_shipping_fee":False,"enabled":False,"item_flag":"0","channelid":18028,"sizeid":0}],"ds_cat_rcmd_id":"","category_recommend":[],"unlisted":False}
    for k in a.keys():
        if udata[k] != a[k]:
            print(k, udata[k], a[k])
            print("--------------------------------")


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

def auto_stock():
    account_list = ['jihuishi.my','jihuishi.id','jihuishi.th','jihuishi.ph','jihuishi.vn','jihuishi.sg']
    for account in account_list:
        account, password = mydb('select account, password from password where account=?', (account,))[0]
        upload_stock(account, password)
        

