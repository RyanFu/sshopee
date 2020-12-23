#coding=utf-8  
import sqlite3, json, os, requests, time, threading
from functools import wraps
semaphore = threading.BoundedSemaphore(5)
database_name = r".\shopee.db" 
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

def lock_decorator():
    def inner_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            log_string = func.__name__ + " was called"
            print(log_string)
            semaphore.acquire()
            result = func(*args, **kwargs)
            semaphore.release()
            return result
        return wrapped_function
    return inner_decorator

def multiple_mission(func, args_list):    
    mission_list = []
    for args in args_list:
        mission = threading.Thread(target=func, args = args)
        mission_list.append(mission)
    for mission in mission_list:
        mission.start()
    for mission in mission_list:
        mission.join()
    while threading.active_count() != 1:
        print(threading.active_count())
    print('----all threads done---')











