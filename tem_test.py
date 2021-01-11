#coding=utf-8  
import sqlite3, json, os, requests, time, threading
from functools import wraps

database_name = "../shopee.db" 
# with  sqlite3.connect(database_name) as cc:
#     sql = "select * from password"
#     cu = cc.execute(sql)
#     account, password = cu.fetchone()
#     print(account, password)    

def file_process():
    root_path = r"C:\Users\guoliang\Downloads\shopee 11月 账单"
    file_names = os.listdir(root_path)
    for f in file_names:
        od = "\\".join([root_path, f])
        si = od[-6:-4] + "_"
        nd = "\\".join([root_path, si + f])
        print(od, nd)
        #os.rename(od, nd)


# def logit(logfile='out.log'):
#     def logging_decorator(func):
#         @wraps(func)
#         def wrapped_function(*args, **kwargs):
#             log_string = func.__name__ + " was called"
#             print(log_string)
#             # 打开logfile，并写入内容
#             with open(logfile, 'a') as opened_file:
#                 # 现在将日志打到指定的logfile
#                 opened_file.write(log_string + '\n')
#             return func(*args, **kwargs)
#         return wrapped_function
#     return logging_decorator


def asynic_decor(func):
    def wrapped_function(*args, **kwargs):
        mission = threading.Thread(target=func, args=args, kwargs=kwargs)
        mission.start()
    return wrapped_function

@asynic_decor
def tf(i):
    print(i, "start")
    time.sleep(i)
    print(i, "done")

m = {}
w = {"my":1,"id":2,"th":3,"ph":4,"vn":5,"sg":6,"br":7,"tw":8}
with  sqlite3.connect(database_name) as cc:
    sql = "select account, parent_sku, model_sku, category_id, sold from items;"
    cu = cc.execute(sql)
    for i in cu:
        select account, parent_sku, model_sku, category_id, sold = i
        sku = model_sku if model_sku else parent_sku
        site = account.split(".")[1]

    











