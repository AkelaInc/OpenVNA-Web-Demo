

import os
import sys
if len(sys.argv) > 1 and "debug" in sys.argv:
	SQLALCHEMY_ECHO = True

basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig(object):

	SECRET_KEY = "kjahsdflkjhasdlfkhasdf9823r98uh23rlkjav98(*YLJHL*(YP;ojhljh"
	# flask-assets
	# ------------
	ASSETS_DEST = 'app/static'


	SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'requestlog.db')

	print(("DB: ", SQLALCHEMY_DATABASE_URI))
	SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')


# VNA Defaults:

VNA_IP         = "192.168.1.217"
VNA_PORT       = 1025

VNA_STARTF     =  500
VNA_STOPF      = 6000
VNA_NPTS       =  256
VNA_EXPERIMENT =    1

ARDUINO_COM_PORT = '/dev/ttyACM0'

# Switch interval. In seconds.
# Currently 15 minutes
SWITCH_INTERVAL  = 60 * 15
# SWITCH_INTERVAL  = 15

CYCLE_EXPERIMENTS = [1,2,3]
