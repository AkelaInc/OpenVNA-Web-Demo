

import eventlet
import logging
import time
import config

from flask import current_app
from flask_socketio import emit
from app import app
from app import socketio

run = True

EXPERIMENT_CONFIGS = {
	1 : {
		'start' : 375,
		'stop'  : 1500,
		'npts'  : 1024,
		},
	2 : {
		'start' : 750,
		'stop'  : 1000,
		'npts'  : 512,
		},
	3 : {
		'start' : 375,
		'stop'  : 3500,
		'npts'  : 256,
		},

	# Not used atm.
	4 : {
		'start' : 1000,
		'stop'  : 1000,
		'npts'  : 1000,
		},

}

class TimerThread(object):
	def __init__(self):
		self.log = logging.getLogger("Main.Timer")
		self.interval = config.SWITCH_INTERVAL
		self.rollup_time = time.time()

		self.experiment_idx = 0


	def cycle_switches(self):

		self.log.info("Emitting message: %s, %s", self.rollup_time, time.time())

		with app.app_context():
			exp = config.CYCLE_EXPERIMENTS[self.experiment_idx]
			self.experiment_idx = (self.experiment_idx + 1) % len(config.CYCLE_EXPERIMENTS)

			npts          = EXPERIMENT_CONFIGS[exp]['npts']
			startf, stopf = EXPERIMENT_CONFIGS[exp]['start'], EXPERIMENT_CONFIGS[exp]['stop']


			msg = {
				"src-guid"      : "nooooooope",
				"switch-matrix" :
				{
					"experiment-1" : exp == 1,
					"experiment-2" : exp == 2,
					"experiment-3" : exp == 3,
					"experiment-4" : exp == 4,
				},
				'start-stop' : [startf, stopf],
				'no-points'  : npts,
			}

			app.config['ARBITER'].set_experiment(msg["switch-matrix"])
			app.config['ARBITER'].set_num_points(npts)
			app.config['ARBITER'].set_start_stop_freq(startf, stopf)

			socketio.emit('config', msg, broadcast=True, namespace='/vna_interface')


	def go(self):
		while run:
			have_control = app.config['LOGIN_ARBITER'].anyone_controlling()
			now = time.time()
			if now > self.rollup_time:
				if not have_control:
					self.cycle_switches()
				self.rollup_time += self.interval

			socketio.emit('have_control', [have_control, self.rollup_time - now], broadcast=True, namespace='/vna_interface')
			eventlet.sleep(seconds=1)

		self.log.info("Timer thread exiting")



def start_timer_thread():
	tt_obj = TimerThread()
	eventlet.spawn_n(tt_obj.go)

def stop_timer_thread():
	global run
	run = False
