import time, json, sqlite3
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

database_name = r".\shopee.db" 
driver_path = r'.\chromedriver.exe'
#http://chromedriver.storage.googleapis.com/index.html

def open_sellercenter(account, password, cookie_only):
    print(account, password)
    site = account[-2:]
    ch_options = Options()
    if cookie_only == "1":
        ch_options.add_argument("--headless")
        print("no head")

    driver = webdriver.Chrome(executable_path=driver_path, options=ch_options)
    driver.get('https://seller.{site}.shopee.cn/account/signin'.format(site=site))
    print("find login page")
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_tag_name("input"))
    bs = driver.find_elements_by_tag_name('input')
    bs[0].send_keys(account)
    bs[1].send_keys(password)
    driver.find_element_by_tag_name('button').click()
    print("login done")
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element_by_class_name("num"))
    cookies_raw = driver.get_cookies()
    if cookie_only == "1":  
        driver.quit()

    cookies_json = {}
    for i in cookies_raw:
        k = i["name"]
        v = i["value"]
        cookies_json[k] = v

    cookies_text = json.dumps(cookies_json)
    with  sqlite3.connect(database_name) as cc:
        sql = "insert or replace into cookies values(?, ?, ?)"
        cc.execute(sql, [account, cookies_text, time.ctime()])
        cc.commit()
    return cookies_text


