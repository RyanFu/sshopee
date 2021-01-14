#coding=utf-8  
import sqlite3, json, os, requests, time
import machine_gun

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


# site_list = ['sku', 'my', 'id', 'th', 'ph', 'vn', 'sg', 'br']
# sql = '''select zong.sku, items.category_id from items join zong 
    # on items.parent_sku = zong.sku or items.model_sku = zong.sku 
    # where items.account like ? group by zong.sku order by items.sold;'''
# mp = {}
# with  sqlite3.connect(database_name) as cc:
    # for i in range(1, len(site_list)):
        # site = site_list[i];print(site);
        # cu = cc.execute(sql, ('%' + site,))
        # for row in cu:
            # sku, cat = row
            # vs = mp.get(sku, [0 for i in site_list])
            # vs[0] = sku
            # vs[i] = cat.split('.')[-1]
            # mp[sku] = vs 
    # data = [i for i in mp.values()]
    # print(len(data))
    # sql = 'insert into cat values(?, ?, ?, ?, ?, ?, ?, ?, ?)'
    # cc.executemany(sql, data)
    # cc.commit()

@machine_gun.decor_retry
def f(i):
    print(i)
    assert(i!=2)


for i in range(3):
    f(i)






