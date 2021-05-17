import threading, time, pandas, sqlite3, platform
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,as_completed
from functools import wraps

db_lock = threading.Lock()

if platform.system() == "Windows":
    database_name = "D:/shopee.db"
    driver_path = 'D:/chromedriver_win32/chromedriver.exe'
else:
    database_name = "/root/shopee.db"
    driver_path = "/root/chromedriver.exe"

def mydb(sql, values=(), many=False):
    with sqlite3.connect(database_name) as db:
        if 'select' in sql:
            cur = db.execute(sql, values)
            rv = cur.fetchall()
        else:
            with db_lock:
                if many:
                    db.executemany(sql, values)
                else:
                    db.execute(sql, values)
                db.commit()
            rv = None
    return rv

def snow(tsp=None):
    tsp = int(tsp) if tsp else None
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tsp))
    return t

def unsnow(s):
    st = time.strptime(s,"%Y-%m-%d %H:%M:%S")
    tp = int(time.mktime(st))
    return tp

def data2book(data, name):
    path = './static/{}.xlsx'.format(name)
    book = pandas.ExcelWriter(path)
    df = pandas.DataFrame(data)
    df.to_excel(book, sheet_name='Sheet1', index=False, header=False)
    book.save()
    return path

#新线程伪异步装饰器
def decor_async(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        print('one new thread started for ', func.__name__)
        mission = threading.Thread(target=func, args=args, kwargs=kwargs)
        mission.start()
    return wrapped_function

#失败重试装饰器
def decor_retry(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except:
            print(func.__name__, " failed , try again later")
            time.sleep(5)
            result = func(*args, **kwargs)
        return result
    return wrapped_function

#多任务并发, 线程版
def multiple_mission(func, args_list, max_number=16):
    num = len(args_list)
    print('total mission number is ', num)
    for i in range(num):
        args = args_list[i]
        while threading.active_count() > max_number + 1:
            print('reach max mission number, waiting...')
            time.sleep(1)
        mission = threading.Thread(target=func, args = args)
        mission.start()
        print('start mission NO.', i)
    return

#多任务并发, 线程版, 加线程池
def multiple_mission_pool(func, args_list, max_workers=16, debug=False):
    if debug:
        arg = args_list[0]
        func(*arg)
        return 
    count, num = 0, len(args_list)
    print('total mission number is ', num)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(func, *args) for args in args_list]
        # for future in as_completed(future_list):
            # result = future.result()
            # count += 1
            # rate = round(count/num, 2)
            # msg = 'total mission {}, completed {}, {}%'.format(num, count, rate)
    print('all missions done')

# #多任务并发,协程版,慢
# def multiple_mission_gevent(func, args_list, max_workers=32):
#     num = len(args_list)
#     print('total mission number is ', num)
#     jobs = [gevent.spawn(func, args) for args in args_list]
#     gevent.wait(jobs)
#     print('all missions done')
#     return