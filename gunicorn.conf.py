import os
import multiprocessing

bind = "0.0.0.0:{}".format(os.environ.get('PORT', 10000))
workers = 1
worker_class = "gthread"
timeout = 120
keepalive = 5
loglevel = "info"
errorlog = "-"
accesslog = "-"
