#coding=utf-8  
import app
import waitress
from shopee_api import mytimer

if __name__ == "__main__":
    mytimer()
    waitress.serve(app.app, port=5001, threads=4, expose_tracebacks=True)


