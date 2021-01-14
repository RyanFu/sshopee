import threading
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,as_completed
from functools import wraps

db_lock = threading.Lock()

#新线程伪异步装饰器
def asy_decor(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        print('one new thread started for ', func.__name__)
        mission = threading.Thread(target=func, args=args, kwargs=kwargs)
        mission.start()
    return wrapped_function

#多任务并发, 线程版
def multiple_mission(func, args_list, max_number=50):
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
def multiple_mission_pool(func, args_list, max_workers=50):
    num = len(args_list)
    print('total mission number is ', num)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        #future = executor.map(get_one, [*args for args in args_list])
        future_list = [executor.submit(func, *args) for args in args_list]
        # for future in as_completed(future_list):
            # result = future.result()
    print('all missions done')

# #多任务并发,协程版,慢
# def multiple_mission_gevent(func, args_list, max_workers=50):
#     num = len(args_list)
#     print('total mission number is ', num)
#     jobs = [gevent.spawn(func, args) for args in args_list]
#     gevent.wait(jobs)
#     print('all missions done')
#     return