#coding=utf-8  
import app
import waitress


if __name__ == "__main__":  
	waitress.serve(app.app, port=5000, threads=4, expose_tracebacks=True)
	# cherrypy.tree.graft(app, '/')
	# cherrypy.config.update({
	# 'server.socket_host': '0.0.0.0',
	# 'server.socket_port': 5000,
	# 'engine.autoreload.on': True,
	# })
	# cherrypy.engine.start()


