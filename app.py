#coding=utf-8 
from flask import Flask, request, render_template, jsonify, redirect
from os import listdir, system
from pandas import read_sql
from datetime import timedelta
import sqlite3, json, time, math, requests, csv
import selenium_chrome, shopee_api

app = Flask(__name__)    
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
database_name = "./shopee.db" 

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def shopee_price(cost, weight, profit_rate = 0):
    weight = math.ceil(weight/10)*10
    cost_rate = 0.06 + 0.02 + 0.02 + 0.04 + 0.02 + 0.02
    exchange_rate = {
    "my": 1.6074,
    "id":  0.000463,
    "tw":  0.2343,
    "ph":  0.1389,
    "vn":  0.00029,
    "th":  0.2146,
    "sg": 4.914,
    "br":  1.1675,
    }
    shipping_fee = {
    "my": weight*0.015,
    "id": weight*120,
    "th": weight*0.2,
    "ph": max(weight*0.45+1, 23),
    "vn": weight*90,
    "sg": max(weight*0.011 + 0.05,0.6),
    "br": min(max(5, weight * 0.14 + 0.8), weight * 0.09 + 5.8),
    } 
    sale_price = { 
    "my": math.ceil((cost+shipping_fee["my"]*exchange_rate["my"])/(1-cost_rate-profit_rate)/exchange_rate['my'] *10)/10,
    "id": math.ceil((cost+shipping_fee["id"]*exchange_rate["id"])/(1-cost_rate-profit_rate)/exchange_rate['id'] /100)*100,
    "th": math.ceil((cost+shipping_fee["th"]*exchange_rate["th"])/(1-cost_rate-profit_rate)/exchange_rate['th'] /1)*1,
    "ph": math.ceil((cost+shipping_fee["ph"]*exchange_rate["ph"])/(1-cost_rate-profit_rate)/exchange_rate['ph'] /1)*1,
    "vn": math.ceil((cost+shipping_fee["vn"]*exchange_rate["vn"])/(1-cost_rate-profit_rate)/exchange_rate['vn'] /100)*100,
    "sg": math.ceil((cost+shipping_fee["sg"]*exchange_rate["sg"])/(1-cost_rate-profit_rate)/exchange_rate['sg'] * 10)/10,
    "br": math.ceil((cost+shipping_fee["br"]*exchange_rate["br"])/(1-cost_rate-0.05-profit_rate)/exchange_rate['br'] * 10)/10,
    }
    return sale_price

@app.route('/', methods = ['GET'])
def defaultPage():
    return redirect("/home")

@app.route('/home', methods = ['GET'])
def HomePage():
    return render_template("home.html")

@app.route('/admin', methods = ['GET'])
def AdminPage():
    return render_template("admin.html")

@app.route('/basic_info', methods = ['GET'])
def basic_info():
    sql = "select account, count(distinct(item_id)), update_time from items group by account order by account asc"
    with sqlite3.connect(database_name) as cc:
        res = cc.execute(sql)
        con = [i for i in res]
    res_data = {"message": "success", "data": con} 
    res_data = jsonify(res_data)
    return res_data

#产品更新接口
@app.route('/shopee_add_items', methods = ['POST'])
def shopee_add_items():
    account = request.json["account"]    
    rows = request.json["rows"][1:]
    sql = "insert into items values (?" + ",?" * 24 + ")"
    rows2delete = [[i[0], i[16]] for i in rows]
    sql2delete = "delete from items where item_id=? and model_id=?"
    with sqlite3.connect(database_name) as cc:
        cc.executemany(sql2delete, rows2delete)
        cc.executemany(sql, rows)
        cc.commit()
    print(time.ctime(), account, "add items complete")
    res_data = {"message": "success", "data": {}}
    res_data = jsonify(res_data)
    return res_data

#活动商品信息匹配
@app.route('/shopee_get_items_by_id', methods = ['POST'])
def get_shopee_items_by_id():
    data = request.json["data"]
    ks = ["items.item_id", "items.parent_sku", "items.original_price", "items.current_price",
        "items.model_id", "items.model_sku", "items.model_original_price", "items.model_current_price",
        "items.rating_star", "items.rating_count", "zong.sku", "zong.cname", "stock.ado", "stock.available", 
         "zong.status", "zong.cost","zong.weight"]

    ks = ",".join(ks)   
    sql = "select " + ks + " from items "
    sql += '''
        join zong on (items.parent_sku != "" and items.parent_sku = zong.sku) 
        or (items.model_sku != "" and items.model_sku = zong.sku)
        join stock on zong.sku = stock.sku
        '''
    sqla = sql + "where items.item_id = ? limit 1"
    sqlb = sql + "where items.item_id = ? and model_id = ? limit 1"
    res_data = {"message": "success", "data": []}  
    with sqlite3.connect(database_name) as cc:            
        for e in data:
            item_id = e["item_id"]
            model_id = e["model_id"]
            if model_id:
                res = cc.execute(sqlb, [item_id, model_id])
            else:
                res = cc.execute(sqla, [item_id])   
            con = res.fetchone()
            if con == None: con = [item_id, model_id]
            res_data["data"].append(con)
        cc.commit()
    print(time.ctime(), "query complete")
    res_data = jsonify(res_data)
    return res_data

#按账号导出全部商品
@app.route('/export_by_account', methods = ['POST'])
def export_by_account():
    account = request.json["account"]

    with  sqlite3.connect(database_name) as cc:
        t1 = time.time()        
        sql = '''select * from items 
        join zong on (items.parent_sku != "" and items.parent_sku = zong.sku) 
        or (items.model_sku != "" and items.model_sku = zong.sku) 
        join stock on zong.sku = stock.sku 
        where account = "{account}"
        '''.format(account=account)
        df = read_sql(sql, cc)
        t2 = time.time()
        file_name = "./static/{account}.csv".format(account=account)
        df.to_csv(file_name)
        t3 = time.time()
        print("读", t2-t1, "写", t3-t2)
    res_data = {"message": "success", "data": {}}
    res_data["data"]["file_name"] = account + ".csv"
    res_data = jsonify(res_data)
    return res_data

#按账号排查库存异常更新
@app.route('/wrong_stock_by_account', methods = ['POST'])
def wrong_stock_by_account():
    account = request.json["account"]
    with  sqlite3.connect(database_name) as cc:
        sql = '''select items.item_id, items.name, 
        items.model_id, items.model_name, 
        items.parent_sku, items.model_sku, 
        items.model_current_price, items.model_stock, 
        zong.status, zong.cname 
        from items 
        join zong on (items.parent_sku != "" and items.parent_sku = zong.sku) 
        or (items.model_sku != "" and items.model_sku = zong.sku) 
        where account = "{account}" 
        '''.format(account = account)
        cu = cc.execute(sql)
        data = []
        for row in cu:
            if row[8] in ["正常", "仅批量"] and row[7] < 10:
                new_row = [i for i in row]
                new_row[7] = 3000
                data.append(new_row)
            elif row[8] not in ["正常", "仅批量"] and row[7] > 0:
                new_row = [i for i in row]
                new_row[7] = 0
                data.append(new_row)

    res_data = {"message": "success", "data": {"rows": data}}
    res_data = jsonify(res_data)
    return res_data

#价格异常
@app.route('/wrong_price_by_account', methods = ['POST'])
def wrong_price_by_account():
    account = request.json["account"]
    site = account.split(".")[1]

    with  sqlite3.connect(database_name) as cc:
        sql = '''select items.item_id, items.model_id, 
        items.model_current_price, items.model_stock, 
        zong.status, zong.cost, zong.weight, zong.sku,
        zong.cname, items.rating_count
        from items 
        join zong on (items.parent_sku != "" and items.parent_sku = zong.sku) 
        or (items.model_sku != "" and items.model_sku = zong.sku) 
        where account = "{account}" and items.model_stock > 0
        '''.format(account=account)
        cu = cc.execute(sql)
        data = []
        for row in cu:
            price_min = shopee_price(row[5], row[6], 0.05)[site]
            price_max = shopee_price(row[5], row[6], 0.25)[site]
            price_current = row[2]
            if price_current > price_max or price_current < price_min:
                new_row = [i for i in row]
                data.append(new_row)
    res_data = {"message": "success", "data": {"rows": data}}
    res_data = jsonify(res_data)
    return res_data

#条件搜索
@app.route('/shopee_search', methods=['POST'])
def shopee_search():
    sql = '''select items.item_id,items.model_id from items 
        join stock on (items.parent_sku != "" and items.parent_sku = stock.sku) 
        or (items.model_sku != "" and items.model_sku = stock.sku) where '''
    con = []
    data = request.json
    if data["sku"]:
        con.append("(items.parent_sku = '{}' or items.model_sku = '{}')".format(data["sku"], data["sku"]))
        sql = sql.replace("select", "select items.account,items.create_time,")
    else:
        if data["account"]:
            con.append("items.account = '{account}'".format(account=data["account"]))
        if data["rating"]:
            con.append("items.rating_star >= {rating}".format(rating=data["rating"]))
        if data["ado"]:
            con.append("stock.ado >= {ado}".format(ado=data["ado"]))
        if not data["multi_model"]:
            con.append("items.model_sku = '' ")
        if data["sold"]:
            con.append("items.sold >= {sold}".format(ado=data["ado"]))
    sql += " and ".join(con)
    print(sql) 

    with  sqlite3.connect(database_name) as cc:
        cu = cc.execute(sql)
        con = cu.fetchall()

    res_data = {"message": "success", "data": {}}
    res_data["data"] = con
    res_data = jsonify(res_data)
    return res_data

#未使用
@app.route('/shopee_cookies', methods=['POST'])
def shopee_cookies():
    data = request.json
    account = data["account"]
    update_time = data["update_time"]
    cookies = data["cookies"]
    sqla = "delete from login where account = ?"
    sqlb = "insert into login values (?, ?, ?)"
    with  sqlite3.connect(database_name) as cc:
        cc.execute(sqla, [account])
        cc.execute(sqlb, [account, update_time, cookies])
    res_data = {"message": "success", "data": {}}
    res_data = jsonify(res_data)
    return res_data    

#批量排查违禁品SKU
@app.route('/wrong_sku', methods=['POST'])
def wrong_sku():
    data = request.json
    sku_list = [i for i in data["sku_list"] if i !=""]
    sql = '''select account, update_time, item_id, model_id,
    parent_sku, model_sku from items 
    where parent_sku = ? or model_sku = ? '''
    res_data = {"message": "success", "data": {"rows":[]}}
    with  sqlite3.connect(database_name) as cc:
        for sku in sku_list:
            cu = cc.execute(sql, [sku, sku])
            [res_data["data"]["rows"].append(i) for i in cu]
    
    res_data = jsonify(res_data)
    return res_data

#前台 刊登前排除重复SKU
@app.route('/duplicate_sku_by_account', methods=['POST'])
def duplicate_sku_by_account():
    data = request.json
    account = data["account"]
    sku_list = [i for i in data["sku_list"] if i !=""]
    sql = '''select * from items 
    where (parent_sku = ? or model_sku = ?) and account = ? limit 1'''
    exsit = []
    with  sqlite3.connect(database_name) as cc:
        for sku in sku_list:
            cu = cc.execute(sql, [sku, sku, account])
            con = cu.fetchone()
            if con != None:          
                exsit.append(sku)            
    non_exist = list(set(sku_list) - set(exsit))
    res_data = {"message": "success", "data": {"skus":non_exist}}
    res_data = jsonify(res_data)
    return res_data         

#管理后台初始信息
@app.route('/account_info', methods=['GET'])
def account_info():
    sql = '''select password.account, password.password,
    cookies.cookies, cookies.update_time 
    from password left join cookies 
    on password.account = cookies.account 
    order by password.account asc
    '''
    with  sqlite3.connect(database_name) as cc:
        cu = cc.execute(sql)
        con = cu.fetchall()
        res_data = {"message": "success", "data": con}
    res_data = jsonify(res_data)
    return res_data 

# 打开后台 获取COOKIES
@app.route('/open_sellercenter', methods=['GET'])
def open_sellercenter():
    account = request.args["account"]
    password = request.args["password"]
    cookie_only = request.args["cookie_only"]
    cookies_text = selenium_chrome.open_sellercenter(account, password, cookie_only)
    res_data = {"message": "success", "data":{"cookies": cookies_text}}
    res_data = jsonify(res_data)
    return res_data 

#按账号更新全部在线产品
@app.route('/update_all_listing', methods=['GET'])
def update_all_listing():
    account = request.args["account"]
    shopee_api.check_cookie_jar(account)
    shopee_api.clear_listing(account)
    shopee_api.get_all_page(account)
    #shopee_api.get_single_page(account)
    res_data = {"message": "success", "data":{}}
    res_data = jsonify(res_data)
    return res_data

#转发到ERP的API避免CORS
@app.route('/redirect_to_erp', methods=['POST'])
def redirect_to_erp():
    data = request.data
    headers = {"content-type" : "text/xml; charset=utf-8"}
    url = "http://runbu.irobotbox.com/Api/API_ProductInfoManage.asmx"
    res = requests.post(url, data=data, headers=headers)
    data = res.text
    return data

#接收文件
@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    file_path = './static/' + file.filename
    print('files ready', time.ctime())
    file.save(file_path)
    msg = file.filename + ' saved.'
    if "csv" in file_path:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            csvrows = csv.reader(csvfile)
            csvrows = [i for i in csvrows][1:]
        batch = 12000
        tb = file.filename.split(".")[0]
        num = len(csvrows[0])
        ph = ','.join(['?'] * num)
        sql = 'insert into {tb} values ( {ph} )'.format(tb=tb, ph=ph)
        with  sqlite3.connect(database_name) as cc:
            cc.execute("delete from {tb}".format(tb=tb))
            cc.executemany(sql, csvrows)
            cc.commit()
        print("zong table update done", time.ctime())
        msg =  'table zong updaed'


    print(file_path)
    print(file_path)
    return "success"

@app.route('/download_table', methods=['GET'])
def download_table():
    tb = request.args["table"]
    cm = 'sqlite3 -header -csv ./shopee.db "select * from {tb};" > ./static/{tb}.csv'.format(tb=tb)
    system(cm)
    url = '/static/{tb}.csv'.format(tb=tb)
    res_data = {"message": "success", "data":url}
    res_data = jsonify(res_data)
    return res_data

#获取后缀
@app.route('/get_sufix', methods=['GET'])
def get_sufix():
    sql = "select account, name, image, description from sufix"
    with  sqlite3.connect(database_name) as cc:
        cu = cc.execute(sql)
        con = cu.fetchall()
    sufix = {}
    for i in con:
        sufix[i[0]] = i[1:]
    res_data = {"message": "success", "data":sufix}
    res_data = jsonify(res_data)
    return res_data

if __name__ == "__main__":    
        app.debug = True
        app.run(port=5001)

