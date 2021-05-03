#coding=utf-8 
from flask import Flask, request, render_template, jsonify, redirect, session, flash
from os import listdir, system
from functools import wraps
from pandas import read_sql
from datetime import timedelta
import sqlite3, json, time, requests, csv, platform, random
import shopee_api
from api_tools import mydb, snow, multiple_mission_pool
from api_robot import sku_info_excel

log = {'data':[], 'time':time.time()}
app = Flask(__name__)   
app.secret_key = '9dsm8G9OSYlJy64mig9KeXJmp' 
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
env = platform.system()
if env == "Windows":
    database_name = "D:/shopee.db" 
else:
    database_name = "/root/shopee.db"

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.before_request
def requests_log():
    ip, path = request.remote_addr, request.path
    if 'static' not in path:
        json, args = request.json, request.args
        args = [(e, args(e)) for e in args]
        json, args = str(json), str(args)
        row = [snow(), ip, path, json, args]
        log['data'].append(row)
        if len(log['data']) > 10 or time.time() - log['time'] > 60:
            log['time'] = time.time()
            sql = 'insert into request_logs values(?,?,?,?,?)'
            mydb(sql, log['data'], True)
            log['data'] = []
        #print(row)

#登录权限检查
def login_required(func):
	@wraps(func)  # 保存原来函数的所有属性,包括文件名
	def inner(*args, **kwargs):
		if session.get("username"):
			ret = func(*args, **kwargs)
			return ret
		else:
			return redirect("/shopee_login")
	return inner

#登录页面  
@app.route('/shopee_login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        username = session.get('username', None)
        if username:
            flash(username + '已经登录') 
            return redirect('/shopee_admin')
        else:
            return render_template("login.html")
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        print(request.form)
        if username == "guoliang" and password == "gl23r42":
            session['username'] = username
            session.permanent = True
            flash(username + '登录成功') 
            return redirect('/shopee_admin')
        else:
            flash(username + '登录失败') 
            return redirect('/shopee_login')
    return render_template("login.html")

#退出
@app.route('/shopee_logout', methods=['GET'])
def logout():
    session.clear()
    flash("已退出登录")
    return redirect('/shopee_login')

#当前用户状态
@app.route('/login_status', methods=['GET'])
def login_status():
    if session:
        name = session['username']
    else:
        name = ''
    res_data = {"message": "success", "username": name}
    res_data = jsonify(res_data)
    return res_data

#常用基础页面
@app.route('/', methods = ['GET'])
def defaultPage_a():
    return redirect("/shopee_listing")

@app.route('/home', methods = ['GET'])
def defaultPage_b():
    return redirect("/shopee_listing")

@app.route('/shopee_listing', methods = ['GET'])
def homePage():
    return render_template("home.html")

@app.route('/shopee_index', methods = ['GET'])
def indexPage():
    return render_template("index.html")

@app.route('/shopee_admin')
@login_required
def adminPage():
    return render_template('admin.html')
    
@app.route('/shopee_dashboard', methods = ['GET'])
def dashboardPage():
    return render_template("dashboard.html")

@app.route('/shopee_orders', methods = ['GET'])
def orderPage():
    return render_template("orders.html")

@app.route('/shopee_wait', methods = ['GET'])
def waitPage():
    return render_template("wait.html")

@app.route('/shopee_console', methods = ['GET'])
@login_required
def consolePage():
    return render_template("console.html")

@app.route('/shopee_collection', methods = ['GET'])
def collectionPage():
    return render_template("collection.html")

#前台初始化
@app.route('/basic_info', methods = ['GET'])
def basic_info():
    sql = "select * from listings_count order by account asc"
    sql2 = "select update_time from log where name = 'zong'"
    sql3 = "select update_time from log where name = 'stock'"
    with sqlite3.connect(database_name) as cc:
        res = cc.execute(sql)
        con = [i for i in res]
        zong_time = cc.execute(sql2).fetchone()
        stock_time = cc.execute(sql3).fetchone()
        zong_time = zong_time[0] if zong_time else ""
        stock_time = stock_time[0] if stock_time else ""
    info = [zong_time, stock_time]
    res_data = {"message": "success", "data": con, "info": info} 
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
    cw = list(zip(df['cost'], df['weight'], df['current_price']))
    df['0%price'] = [shopee_api.shopee_price(float(i),int(j),0)[account[-2:]] for i, j, k in cw]
    df['5%price'] = [shopee_api.shopee_price(float(i),int(j),0.05)[account[-2:]] for i, j, k in cw]
    df['10%price'] = [shopee_api.shopee_price(float(i),int(j),0.1)[account[-2:]] for i, j, k in cw]
    df['15%price'] = [shopee_api.shopee_price(float(i),int(j),0.15)[account[-2:]] for i, j, k in cw]
    df['20%price'] = [shopee_api.shopee_price(float(i),int(j),0.2)[account[-2:]] for i, j, k in cw]
    #df['profit_rate'] = [shopee_rate(float(i),int(j),float(k))[account[-2:]] for i, j, k in cw]
    file_name = "./static/{account}.xlsx".format(account=account)
    df.to_excel(file_name, index=False)
    t3 = time.time()
    print("读", t2-t1, "写", t3-t2)
    res_data = {"message": "success", "data": {}}
    res_data["data"]["file_name"] = account + ".xlsx"
    res_data = jsonify(res_data)
    return res_data

#按账号排查库存异常 按产品状态
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
        left join zong on (items.parent_sku != "" and items.parent_sku = zong.sku) 
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
            elif row[8] in ["清库", "停产", "暂时缺货"] and row[7] > 0:
                new_row = [i for i in row]
                new_row[7] = 0
                data.append(new_row)

    res_data = {"message": "success", "data": {"rows": data}}
    res_data = jsonify(res_data)
    return res_data

#按账号排查库存异常 按实际库存
@app.route('/wrong_stock_by_account_hard', methods = ['POST'])
def wrong_stock_by_account_hard():
    account = request.json["account"]
    sql = '''select items.item_id, items.name, 
    items.model_id, items.model_name, 
    items.parent_sku, items.model_sku, 
    items.model_current_price, items.model_stock, 
    stock.total, items.sold  
    from items 
    left join stock on (items.parent_sku != "" and items.parent_sku = stock.sku) 
    or (items.model_sku != "" and items.model_sku = stock.sku) 
    where account = ? '''
    cu = mydb(sql, (account,))
    data = []
    for row in cu:   
        new_row = [i for i in row]
        new_row[8] = 0 if new_row[8] is None else new_row[8]
        if new_row[7] == new_row[8]:
            continue
        if new_row[8] <= 0:
            if new_row[7] > 0:       
                new_row[7] = 0
                data.append(new_row)
        elif new_row[8] <= 3:       
            new_row[7] = new_row[8]
            data.append(new_row)
        elif new_row[8] > 3 and new_row[7] < 3:       
            new_row[7] = 300
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
            price_min = shopee_api.shopee_price(row[5], row[6], 0.05)[site]
            price_max = shopee_api.shopee_price(row[5], row[6], 0.25)[site]
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
    sql = '''select items.item_id,items.model_id, items.account, 
        items.sold, items.rating_star from items 
        join stock on (items.parent_sku != "" and items.parent_sku = stock.sku) 
        or (items.model_sku != "" and items.model_sku = stock.sku) where '''
    con = []
    data = request.json
    if data["sku"]:
        con.append("(items.parent_sku = '{}' or items.model_sku = '{}')".format(data["sku"], data["sku"]))
        #sql = sql.replace("select", "select items.account,items.create_time,")
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
            con.append("items.sold >= {sold}".format(sold=data["sold"]))
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
    sql = '''select item_id, model_id,account, model_sold, 
    parent_sku, model_sku, update_time from items 
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
    sql = '''select password.account, password.account,
    cookies.cookies, cookies.update_time 
    from password left join cookies 
    on password.account = cookies.account 
    order by password.account asc
    '''
    with  sqlite3.connect(database_name) as cc:
        cu = cc.execute(sql)
        con = cu.fetchall()
    res_data = {"message": "success", "data": con, "platform":platform.system()}
    res_data = jsonify(res_data)
    return res_data

#检查并更新COOKIES
@app.route('/get_update_cookie_jar', methods=['GET'])
def get_update_cookie_jar():
    account = request.args["account"]
    shopee_api.check_cookie_jar(account)
    res_data = {"message": "success", "data":{"cookies": "success"}}
    res_data = jsonify(res_data)
    return res_data   

# 打开后台 
@app.route('/open_sellercenter', methods=['GET'])
@login_required
def open_sellercenter():
    account = request.args["account"]
    cookie_only = False
    with  sqlite3.connect(database_name) as cc:
        sql = 'select account, password from password where account=? limit 1'
        cu = cc.execute(sql, (account,))
        password = cu.fetchone()[1]
    cookies_text = shopee_api.open_sellercenter(account, password, cookie_only)
    res_data = {"message": "success", "data":{"cookies": cookies_text}}
    res_data = jsonify(res_data)
    return res_data 

#按账号更新全部在线产品
@app.route('/update_all_listings', methods=['GET'])
def update_all_listings():
    account = request.args["account"]
    shopee_api.check_cookie_jar(account)
    shopee_api.get_all_page(account)
    res_data = {"message": "success", "data":{}}
    res_data = jsonify(res_data)
    return res_data

#更新全部账号在线产品
@app.route('/update_all_accounts_listings', methods=['GET'])
def update_all_accounts_listings():
    sql = 'select account from password'
    con = mydb(sql)
    account_list = [i[0] for i in con]
    for account in account_list:
        print('now for ', account)
        sql = 'select update_time from items where account=? limit 1'
        update_time = mydb(sql, (account,))
        update_time = update_time[0][0] if update_time else '0'
        tsp = time.time() - 60 * 60 * 3
        lasthour = snow(tsp)
        if update_time < lasthour or update_time > snow():
            print(account, ' will update')
            shopee_api.check_cookie_jar(account)
            shopee_api.get_all_page(account)
            time.sleep(5)
        else:
            print(account, ' updated')
    res_data = {"message": "success", "data":{}}
    res_data = jsonify(res_data)
    return res_data

#单个账号表现
@app.route('/update_shop_performance', methods=['GET'])
def update_shop_performance():
    account = request.args["account"]
    shopee_api.check_cookie_jar(account)
    values = shopee_api.get_performance(account)
    keys = ["account", "follower_count", "item_count", "rating_star", "rating_count", "pre_sale_rate", "points", 
    "response_rate", "non_fulfill_rate", "cancel_rate", "refund_rate", "apt", "late_shipping_rate"]
    con = values
    res_data = {"message": "success", "data":con}
    res_data = jsonify(res_data)
    return res_data

#全部账号表现更新
@app.route('/update_all_shop_performance', methods=['GET'])
def update_all_shop_performance():
    shopee_api.get_all_performance()
    res_data = {"message": "success", "data":[]}
    res_data = jsonify(res_data)
    flash("账号表现已更新")
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

#
@app.route('/sku_info_excel', methods=['POST'])
def sku_info_excel_view():
    user_name,user_password = request.json['user_name'], request.json['user_password']
    sku_list, acsi = request.json['sku_list'], request.json['acsi']
    name = sku_info_excel(user_name,user_password, sku_list, acsi)
    res_data = {"message": "success", "name":name}
    res_data = jsonify(res_data)
    return res_data

#接收文件
@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    file_path = './static/' + file.filename
    print('files uploaded', time.ctime())
    file.save(file_path)
    msg = file.filename + ' saved'
    if "csv" in file_path:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            csvrows = csv.reader(csvfile)
            csvrows = [i for i in csvrows][1:]
        print('csv files read')
        batch = 12000
        tb = file.filename.split(".")[0]
        num = len(csvrows[0])
        ph = ','.join(['?'] * num)
        sql = 'insert into {tb} values ( {ph} )'.format(tb=tb, ph=ph)
        sql_up = 'insert or replace into log values(?, ?)'
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with  sqlite3.connect(database_name) as cc:
            cc.execute("delete from {tb}".format(tb=tb))
            cc.executemany(sql, csvrows)          
            cc.execute(sql_up,(tb, update_time))
            cc.commit()
        print("table updated", time.ctime())
        if tb in ['stock', 'zong']:
            sql = 'delete from {} where sku = ""'.format(tb)
            mydb(sql)
        msg += ' as table'

    print(file_path)
    return msg

#按名称导出文件为CSV文件
@app.route('/download_table', methods=['GET'])
@login_required
def download_table():
    tb, tp = request.args["table"].split('.')
    if tp == 'table':
        key = ''.join([chr(random.randrange(65,90)) + chr(random.randrange(97,122)) for i in range(12)])
        tn = tb + '_table_' + key
        cm_output = 'sqlite3 -header -csv ../shopee.db "select * from {tb};" > ./static/{tn}.csv'.format(tb=tb,tn=tn)
        cm_zip = 'zip -m -P redback12 ./static/{tb}.zip ./static/{tb}.csv'.format(tb=tb)
        system(cm_output)
        #system(cm_zip)
        url = '/static/{tn}.csv'.format(tn=tn)
    else:
        url = '/static/{tb}.{tp}'.format(tb=tb, tp=tp)
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

#在线数量分析
@app.route('/listings_count', methods=['GET'])
def listings_count():
    day10 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 60*60*24*7))
    day30 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 60*60*24*30))
    day60 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 60*60*24*60))
    sql = '''select account from password order by account'''
    sqla = '''select account, count( distinct item_id) from items 
    where create_time > ?  
    group by account '''
    sqlc = '''select account, count( distinct item_id) from items 
    where create_time > ? and  create_time < ? 
    group by account '''
    sqld = '''select account, count( distinct item_id) from items 
    where create_time > ? and  create_time < ? and sold >= 1 
    group by account '''
    sqle = '''select account, count( distinct item_id) from items group by account'''
    sqlf = 'select account, max(create_time) from items group by account'
    sqlg = 'select account, min(update_time) from items group by account'
    sql_up = '''insert into listings_count 
    values (?,?,?,?,?,?,?,?) '''

    cu0 = mydb(sql)
    cu1 = mydb(sqla, (day10,))   
    cu2 = mydb(sqla, (day30,))
    cu3 = mydb(sqlc, (day60, day30))
    cu4 = mydb(sqld, (day60, day30))
    cu5 = mydb(sqle)
    cu6 = mydb(sqlf)
    cu7 = mydb(sqlg)

    mp = {}
    for i in cu0:
        account = i[0]
        mp[account] = [account,0,0,0,0,0,0,0]
    cus = [cu0, cu1, cu2, cu3, cu4, cu5,cu6,cu7]
    for i in range(1, len(cus)):
        cu = cus[i]
        for j in cu:
            account, num = j
            mp[account][i] = num

    values = [i for i in mp.values()]
    mydb('delete from listings_count')
    mydb(sql_up, values, True)

    flash("刊登统计已更新")
    res_data = {"message": "success", "data":values}
    res_data = jsonify(res_data)
    return res_data

#EASYUI网格数据查询
@app.route('/easyui/<name>/<action>', methods=['GET', 'POST'])
def easyui(name, action):
    #print(action, request.args,request.json,request.form)
    #未登录用户只允许访问白名单表, 权限为只查看
    black_list = ['password', 'cookies']
    if session.get('username', None) is None:
        if action != 'get' or name in black_list:
            flash('当前数据需要登录权限')
            return redirect('/shopee_login')

    if action == 'get':
        page = int(request.form['page'])
        rows = int(request.form['rows'])
        offset = rows * (page - 1)
        sql = 'select * from {name}'.format(name=name)
        with  sqlite3.connect(database_name) as cc:
            cc.row_factory = dict_factory
            con = cc.execute(sql).fetchall()
        res_data = {'total':len(con), 'rows': con[offset: offset + rows]}

    elif action == 'save':
        keys = [i for i in request.form.keys()][1:]
        values = [request.form[i] for i in keys]
        ph = ','.join(['?' for i in values])
        keys = ','.join(keys)
        sql = 'insert into {name} ({keys}) values({ph})'.format(name=name, keys=keys, ph=ph)
        with  sqlite3.connect(database_name) as cc:
            print(sql)
            cc.execute(sql, values)
            cc.commit()       
            res_data = {}

    elif action == 'delete':
        num = request.form['id']
        sql = 'delete from {name} where id = ?'.format(name=name)
        with  sqlite3.connect(database_name) as cc:
            print(sql)
            cc.execute(sql, (num,))
            cc.commit()       
            res_data = {'success': True}

    elif action == 'update':
        num = request.form['id']
        keys = [i for i in request.form.keys()]
        sql = 'update {} set '.format(name)
        data = []
        res_data = {}
        for k in keys:
            if k != 'id':
                sql += '{} = ?,'.format(k)
                data.append(request.form[k])
            res_data[k] = request.form[k]
        sql = sql[:-1] + ' where id = ?'
        sql2 = 'select * from {} where id = ? '.format(name)
        data.append(num)
        with  sqlite3.connect(database_name) as cc:
            print(sql, data)
            cc.execute(sql, data)
            cc.commit()
            
    res_data = jsonify(res_data)
    return res_data

#SQL在线查询
@app.route('/select_output', methods=['POST'])
@login_required
def select_output():
    sql = request.json["sql"]
    con = mydb(sql)
    res_data = {"message": "success", "data": con}
    res_data = jsonify(res_data)
    return res_data

#获取取消订单列表
@app.route('/get_cancellation_orders', methods=['GET'])
def get_cancellation_orders():
    shopee_api.get_all_cancellations()
    res_data = {}
    res_data = jsonify(res_data)
    flash("取消订单已更新")
    return res_data

#取消订单处理
@app.route('/process_cancellation_order', methods=['POST'])
@login_required
def process_cancellation_order():
    data = request.json
    message = ''
    for row in data['data']:
        account, order_id, action = row['account'], row['order_id'], row['action']
        data = shopee_api.cancellation_reject_accept(account, order_id, action)
        message += str(row['order_sn']) + ' ' + data['message'] + "; "
    res_data = {}
    res_data = jsonify(res_data)
    flash(message)
    return res_data
    
#获取退款订单列表
@app.route('/get_return_orders', methods=['GET'])
def get_return_orders():
    shopee_api.get_all_returns()
    res_data = {}
    res_data = jsonify(res_data)
    flash("退款订单已更新")
    return res_data

#订单跟踪号获取
@app.route('/get_orders_details', methods=['GET'])
def get_orders_details():
    account, sn = request.args["account"], request.args["sn"]
    shopee_api.check_cookie_jar(account)
    data = shopee_api.sn2details(account, sn)
    res_data = {"message": "success", "data": data}
    res_data = jsonify(res_data)
    return res_data

#平台推荐分类
@app.route('/get_recommend_category', methods=['POST'])
def get_recommend_category():
    name_list, account = request.json["name_list"], request.json["account"]
    shopee_api.check_cookie_jar(account)
    data = shopee_api.get_recommend_category(name_list, account)
    res_data = {"message": "success", "data": data}
    res_data = jsonify(res_data)
    return res_data

#修改在线库存
@app.route('/update_stock_account', methods=['POST'])
@login_required
def update_stock_account():
    account, rows = request.json["account"], request.json["rows"]
    shopee_api.check_cookie_jar(account)
    cookies = shopee_api.get_cookie_jar(account)
    values = [[account, cookies, int(i[0]), int(i[1]), int(i[2])] for i in rows]    
    multiple_mission_pool(shopee_api.update_listing, values)
    res_data = {"message": "success", "data": ""}
    res_data = jsonify(res_data)
    return res_data

#确认当前活动价格
@app.route('/update_promotion_account', methods=['POST'])
@login_required
def update_promotion_account():
    account, rows = request.json["account"], request.json["rows"]
    shopee_api.check_cookie_jar(account)
    cookies = shopee_api.get_cookie_jar(account)
    values = [[account, cookies, *i] for i in rows]
    multiple_mission_pool(shopee_api.update_promotion_price, values)
    sql = 'update wait set done = 1 where item_id = ? and model_id  =?'
    values = [i[:2] for i in rows]
    mydb(sql, values, True)
    res_data = {"message": "success", "data": ""}
    res_data = jsonify(res_data)
    return res_data

#提交当前活动价格
@app.route('/wait_promotion_account', methods=['POST'])
def wait_promotion_account():
    account, rows = request.json["account"], request.json["rows"]
    sqla = 'select parent_sku, model_sku from items where item_id = ? and model_id = ?'
    sqlb = 'select cost, weight from zong where sku = ?'
    data = []
    for item_id, model_id, price, account in rows:
        con = mydb(sqla, (item_id, model_id))
        parent_sku, model_sku = con[0] if con else (0,0)
        sku = model_sku if model_sku else parent_sku
        con = mydb(sqlb, (sku,))
        cost, weight = con[0] if con else (0, 0)
        rate = shopee_api.shopee_rate(float(cost), float(weight), float(price))[account[-2:]]
        profit = float(price) * rate
        bprice = float(price) - profit
        row = [item_id, model_id, price, account,sku,cost, weight,bprice,profit,rate,snow(),0]
        data.append(row)
    #print(data)
    mydb('insert into wait values(?,?,?,?,?,?,?,?,?,?,?,?)', data, True)
    res_data = {"message": "success", "data": ""}
    res_data = jsonify(res_data)
    return res_data

#智能分类预测
@app.route('/ai_recommend_category', methods=['POST'])
def ai_recommend_category():
    account, name_list = request.json["account"], request.json["name_list"]   
    data = shopee_api.recommend_category(name_list, account)
    res_data = {"message": "success", "data": data}
    #print(res_data)
    res_data = jsonify(res_data)
    return res_data

#广告情况统计
@app.route('/ad_report', methods=['GET'])
def ad_report():
    data = shopee_api.ad_report()
    res_data = {"message": "success", "data": {}}
    res_data = jsonify(res_data)
    flash('广告统计已更新')
    return res_data

#部分更新总表
@app.route('/uzong_update', methods=['GET'])
def uzong_update():
    mydb("update uzong set status = '仅批量' where status  = '起批量'")
    con =mydb('select uzong.status, uzong.sku from uzong inner join zong on uzong.sku = zong.sku and uzong.status <> zong.status')
    data = [i for i in con]
    num = len(data)
    sql = "update zong set status = ? where sku = ?"
    mydb(sql, data, True)
    res_data = {"message": "success", "data": {}}
    res_data = jsonify(res_data)
    flash(f'总表已部分更新{num}个SKU状态')
    return res_data

@app.route('/name2detail', methods=['POST'])
def name2detail():
    account, name_list = request.json['account'], request.json['name_list']
    mark_list = ', '.join(["'" + i +  "'" for i in name_list])
    #print(mark_list)
    sql = '''with temp as (select item_id, parent_sku, model_sku, name, 0, model_original_price, model_current_price, view, sold, like, rating_count, rating_star, images_count 
    from items where account = ? and name in ({} )) 
    select * from temp left join zong on 
    (temp.parent_sku = zong.sku or temp.model_sku = zong.sku) 
    left join stock on (temp.parent_sku = stock.sku or temp.model_sku = stock.sku)'''.format(mark_list)
    con = mydb(sql, (account,))
    rows = [con[i] for i in range(len(con)) if i == 0 or con[i][0] != con[i-1][0] ]
    rows = [i[3:13] + (i[17], i[18], i[22], i[14], i[16], i[0]) for i in rows]
    res_data = {"message": "success", "data": rows}
    res_data = jsonify(res_data)
    flash(f'匹配成功')
    return res_data
    
@app.route('/get_shopids', methods=['POST'])
def get_shopids():
    site, shopids = request.json['site'], request.json['shopids']
    data = [[i, site, 0] for i in shopids]
    sql = 'insert into shopids values(?,?,?)'
    mydb(sql, data, True)
    res_data = {"message": "success", "data": []}
    res_data = jsonify(res_data)
    return res_data    

@app.route('/auto_follow', methods=['GET'])
def auto_follow():
    account = request.args['account']
    shopee_api.auto_follow(account)
    res_data = {"message": "success", "data": []}
    res_data = jsonify(res_data)
    return res_data 

@app.route('/save_collection', methods=['POST'])
def save_collection():
    row = [
        request.json['user'],
        snow(),
        request.json['sku'],
        request.json['cost'],
        request.json['weight'],
        request.json['name'],
        request.json['des'],
        '',
        0,
        request.json['images'],
    ]
    row[-1] = '\t'.join(row[-1])
    data = []
    request.json['colors'] = [i for i in request.json['colors'] if len(i) > 1]
    if request.json['colors']:
        for c in request.json['colors']:
            nrow = [i for i in row]
            nrow[7] = c
            nrow[2] += '_' + c
            data.append(nrow)
    else:
        data = [row,]
    sql = 'insert into collections values(?,?,?,?,?,?,?,?,?,?)'
    mydb(sql, data, True)
    res_data = {"message": "success", "data": []}
    res_data = jsonify(res_data)
    return res_data 
   
#调试模式运行
if __name__ == "__main__":    
        app.debug = True
        app.run(host='0.0.0.0',port=5001)

