from flask import Flask, request
import sqlite3, json, time

app = Flask(__name__)

config = {
    "databasepath": "shopee.db"
}
       

@app.route('/', methods = ['GET'])
def HomePage():
    return "it is running."


@app.route('/db', methods = ['POST'])
def processSQL():
    data = request.json
    sqls = data["sqls"]
    database_name = config["databasepath"]
    cc =  sqlite3.connect(database_name)
    res_data = {"message": "success", "data": []}
    for sql in sqls:
        res = cc.execute(sql)
        con = [i for i in res]
        res_data["data"].append(con)
    cc.commit()
    cc.close()
    return res_data

@app.route('/shopee_add_items', methods = ['POST'])
def shopee_add_items():
    account = request.json["account"]
    rows = request.json["rows"][1:]
    database_name = config["databasepath"]
    cc =  sqlite3.connect(database_name)
    sql = "delete from items where account='" + account + "'"
    cc.execute(sql)
    sql = "insert into items values (?" + ",?" * 24 + ")"
    cc.executemany(sql, rows)
    cc.commit()
    cc.close()
    res_data = {"message": "success", "data": {}}
    return res_data

@app.route('/zong_add_items', methods = ['POST'])
def zong_add_items():
    rows = request.json["rows"][1:]
    database_name = config["databasepath"]
    cc =  sqlite3.connect(database_name)
    sql = "delete from zong"
    cc.execute(sql)
    sql = "insert into zong values (?, ?, ?, ?, ?)"
    cc.executemany(sql, rows)
    cc.commit()
    cc.close()
    res_data = {"message": "success", "data": {}}
    return res_data

@app.route('/stock_add_items', methods = ['POST'])
def stock_add_items():
    rows = request.json["rows"][1:]
    database_name = config["databasepath"]
    cc =  sqlite3.connect(database_name)
    sql = "delete from stock"
    cc.execute(sql)
    sql = "insert into zong values (?, ?, ?, ?)"
    cc.executemany(sql, rows)
    cc.commit()
    cc.close()
    res_data = {"message": "success", "data": {}}
    return res_data


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
    
    database_name = config["databasepath"]
    cc =  sqlite3.connect(database_name)
    res_data = {"message": "success", "data": []}      
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
    cc.close()
    return res_data
if __name__ == "__main__":
    app.debug = True
    app.run()