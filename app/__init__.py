import os
import datetime
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from config import basedir
from babel.dates import format_datetime
from flask.ext.assets import Bundle
from flask.ext.assets import Environment
from flask_socketio import SocketIO
import urllib.parse



app = Flask(__name__)

import sys
if "debug" in sys.argv:
	print("Flask running in debug mode!")
	app.debug = True
app.config.from_object('config.BaseConfig')
# app.jinja_env.add_extension('jinja2.ext.do')

if "debug" in sys.argv:
	print("Installing debug toolbar!")
	toolbar = DebugToolbarExtension(app)


# app.config['ASSETS_DEBUG'] = True
assets = Environment(app)

db = SQLAlchemy(app)

js_plots = Bundle(
				'js/socket.io.js',
				'js/msgpack.js',
				'js/bootstrap-number-input.js',
				'js/flot/jquery.flot.js',
				'js/flot/jquery.flot.selection.js',
				'js/flot/jquery.flot.axislabels.js',
				'js/jquery.easing.1.3.js',
				'js/jquery.bouncebox.1.0.js',
				'js/bootbox.js',
				'js/vna_app.js',
		filters='slimit',
		output='gen/vna_app.js')

js_base = Bundle(
				'js/jquery-latest.js',
				'js/bootstrap.js',
		filters='slimit',
		output='gen/base.js')

css_base = Bundle(
				'css/bootstrap.css',
				'css/custom.css',
		filters='cssmin',
		output='gen/base.css')

assets.register('js_plots', js_plots)
assets.register('js_base', js_base)
assets.register('css_base', css_base)

socketio = SocketIO(app)

# ========================================================

from app import views

@app.context_processor
def utility_processor():

	def format_date(value):
		return format_datetime(value, "EE yyyy.MM.dd")

	def date_now():
		return format_datetime(datetime.datetime.today(), "yyyy/MM/dd, hh:mm:ss")


	return dict(
			format_date        = format_date,
			date_now           = date_now,
			)
