#coding=utf-8  
import app
import waitress

if __name__ == "__main__":
	waitress.serve(app.app, port=5000, threads=4, expose_tracebacks=True)


