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


@app.route('/shopee_get_items_by_id', methods = ['POST'])
def get_shopee_items_by_id():
    t1 = time.time()
    data = request.json["data"]
    ks = ["item_id", "parent_sku", "original_price", "current_price","model_id", "model_sku", "model_original_price", "model_current_price"]
    ks = ",".join(ks)   
    sqla = "select " + ks + " from items where item_id=? limit 1" 
    sqlb = "select " + ks + " from items where item_id=? and model_id=? limit 1" 
    
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
        res_data["data"].append(con)
    cc.commit()
    cc.close()
    t2 = time.time()
    print(t2-t1)
    return res_data


app.debug = True
app.run()