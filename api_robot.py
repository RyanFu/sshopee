import requests, random, pandas
from bs4 import BeautifulSoup as sp
from api_tools import mydb
from shopee_api import shopee_price, recommend_category

channel_map = {"my": "channel_id_28016", "id": "channel_id_88001",
               "th": "channel_id_78004", "ph": "channel_id_48002",
               "vn": "channel_id_58007", "sg": "channel_id_18025",
               "br": "channel_id_90001", "mx": "channel_id_100001"}

hd = ["ps_category","ps_product_name","ps_product_description","ps_sku_parent_short",
      "et_title_variation_integration_no","et_title_variation_1","et_title_option_for_variation_1",
      "et_title_image_per_variation","et_title_variation_2","et_title_option_for_variation_2",
      "ps_price","ps_stock","ps_sku_short","ps_item_cover_image",
      "ps_item_image_1","ps_item_image_2","ps_item_image_3","ps_item_image_4","ps_item_image_5",
      "ps_item_image_6","ps_item_image_7","ps_item_image_8",
      "ps_weight","ps_length","ps_width","ps_height","channel_id_78004","ps_product_pre_order_dts", ""]

def login_check(user_name,user_password):
    sku_list = ['HA003327-00',]
    sku_list = ",".join(sku_list)
    ev = '''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
            <GetProducts xmlns="http://tempuri.org/">
            <productRequest>
            <CustomerID>1551</CustomerID>
            <UserName>{}</UserName>
            <Password>{}</Password>
            <ClientSKUs>{}</ClientSKUs>
            </productRequest>
            </GetProducts>
            </soap:Body>
            </soap:Envelope>'''.format(user_name,user_password, sku_list)
    headers = {"content-type" : "text/xml; charset=utf-8"}
    url = "http://runbu.irobotbox.com/Api/API_ProductInfoManage.asmx"
    res = requests.post(url, data=ev, headers=headers)
    if 'UserNamePassWordError' in res.text:
        return False
    else:
        return True

def read_sku_info(user_name,user_password, sku_list):
    sku_list = ",".join(sku_list)
    ev = '''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
            <GetProducts xmlns="http://tempuri.org/">
            <productRequest>
            <CustomerID>1551</CustomerID>
            <UserName>{}</UserName>
            <Password>{}</Password>
            <ClientSKUs>{}</ClientSKUs>
            </productRequest>
            </GetProducts>
            </soap:Body>
            </soap:Envelope>'''.format(user_name,user_password, sku_list)
    headers = {"content-type" : "text/xml; charset=utf-8"}
    url = "http://runbu.irobotbox.com/Api/API_ProductInfoManage.asmx"
    res = requests.post(url, data=ev, headers=headers)

    h = sp(res.text, 'xml')
    rows = h.findAll('ApiProductInfo')
    keys = ['ClientSKU', 'ProductNameCN', 'ProductName', 'ProductDescription', 'LastSupplierPrice', 'GrossWeight']
    data = []
    for r in rows:
        mp = {}
        for k in keys:
            mp[k] = r.find(k).string
        images = [i.find('ImageUrl').string for i in r.findAll('ApiProductImage') ]
        covers = [i.find('ImageUrl').string for i in r.findAll('ApiProductImage') if i.find('IsCover').string == 'true']
        if covers:
            idx = images.index(covers[0])
            images[0], images[idx] = images[idx], images[0]
        mp['images'] = images
        data.append(mp)
    return data

def mp2row(mp, sufix, acsi):
    account, site = acsi.split('.')
    name = mp['ProductName'].split(',')[0] + ' ' + sufix[0]
    ps = [('<br/>', '\n'), ('<br/>\n', '\n'), 
    ('<br />', '\n'), ('<br />\n', '\n'),('\n\n', '\n'), 
    ('Specif', '\nSpecif'), ('Note', '\nNote'), 
    ('Package', '\nPackage'),('\n\n\n', '\n\n'),]
    for oritxt, newtxt in ps:
        mp['ProductDescription'] = mp['ProductDescription'].replace(oritxt, newtxt)
    des = mp['ProductDescription'] + '\n\n' + sufix[1]
    bs = sufix[2]
    pos = random.choice(["nw", "sw", "ne", "se"])
    sfimg = '?x-oss-process=image/watermark,size_80,color_FFFFFF,t_5,shadow_5,g_{},text_{}'.format(pos, bs)
    images = [i + sfimg for i in mp['images']] + [''] * 9
    cost, weight = float(mp['LastSupplierPrice']),round(float(mp['GrossWeight']) + 5, -1)
    pr = 0.1 if site in ['mx', 'br'] else 0.15
    price = shopee_price(cost, weight, pr)[site]
    weight = weight if site == 'vn' else weight / 1000
    cut = {"my":0.1, "id":100, "th":1, "ph":1, "vn":100, "br":0.1, "sg": 0.1, "mx":0.1}
    price = round(price / 0.6 / cut[site]) * cut[site]
    sku = mp['ClientSKU']
    nrow = [''] * 29
    nrow[0] = mp['cat']
    nrow[1:3] = [name, des]
    nrow[10:12] = [price, 300]
    nrow[13:22] = images[:9]
    nrow[22], nrow[26] = weight, '开启'
    if '-00' in sku or '-' not in sku:
        nrow[3] = sku
    else:
        psku, num = sku.split("-")
        nrow[3:8] = [psku, psku, 'color', 'No.' + num[:2], images[0]]
        nrow[12] = sku
    nrow[28] = mp['ProductNameCN']
    return nrow

def make_excel(data, acsi): 
    df1 = pandas.DataFrame([['内容在第2页']], columns=None)
    data2 = [[],[],[],[],] + data
    df2 = pandas.DataFrame(data2, columns=hd)
    if '.my' in acsi:
        df2.insert(27, 'channel_id_28052', '开启')
    data3 = [["mass_new_basic", '', ''], ["Category name", "Category ID", "Category Pre-order DTS range"]]
    df3 = pandas.DataFrame(data3, columns=None)
    df4 = pandas.DataFrame([['']], columns=None)
    name = './static/4new_' + acsi + '.xlsx'
    with pandas.ExcelWriter(name) as writer:
        df1.to_excel(writer, sheet_name='Guidance', index=False, header=None)
        df2.to_excel(writer, sheet_name='Template', index=False)
        df4.to_excel(writer, sheet_name='Upload Sample', index=False, header=None)
        df3.to_excel(writer, sheet_name='Pre-order DTS Range', index=False, header=None)
    print(name + ' saved')
    name = name.replace('./static/', '')
    return name
 
def sku_info_excel(user_name,user_password, sku_list, acsi):
    hd[26] = channel_map[acsi[-2:]]
    sql = 'select name, description, image from sufix where account = ?'
    sufix = mydb(sql, [acsi[:-3],])[0]
    data = []
    for i in range(0, len(sku_list), 49):      
        data += read_sku_info(user_name,user_password, sku_list[i: i+49])
    data = [i for i in data if i['ProductName'] and i['ProductDescription']]
    name_list = [r['ProductName'] for r in data]
    cat_res = recommend_category(name_list, acsi)
    cat_list = [i[1] for i in cat_res]
    cat_name_list = [i[2] for i in cat_res]
    for i in range(len(data)):
        data[i]['cat'] = cat_list[i]
        data[i]['ProductNameCN'] += cat_name_list[i]
    data.sort(key=lambda x: x['ClientSKU'])
    sheet = [mp2row(mp, sufix, acsi) for mp in data]
    name = make_excel(sheet, acsi)
    return name

def read_collections():
    sql = 'select sku, cost, weight, name, des, color, images from collections'
    con = mydb(sql)
    data = []
    for r in con:
        mp = {}
        mp['ClientSKU'], mp['LastSupplierPrice'], mp['GrossWeight'], mp['ProductName'],mp['ProductDescription'], mp['color'], mp['images'] = r
        mp['images'] = mp['images'].split('\t')
        mp['ProductNameCN'] = ''
        data.append(mp)
    return data
