
try:
	import logSetup
	logSetup.initLogging()
except:
	print("No logging!")
	import traceback
	traceback.print_exc()



import eventlet
eventlet.monkey_patch()


import app.timerthread as timert
from app import socketio
from app import app
import arbiter


def go():

	print("Starting background threads")

	hardware_arb = arbiter.HardwareArbiter()
	login_arb    = arbiter.LoginArbiter()

	app.config['ARBITER'] = hardware_arb
	app.config['LOGIN_ARBITER'] = login_arb

	timert.start_timer_thread()
	try:
		socketio.run(app, port=8080, log_output=True, use_reloader=False)
	except KeyboardInterrupt:
		pass
	print("SocketIO.run returned.")

	timert.stop_timer_thread()

	hardware_arb.close()

	print("Thread halted. App exiting.")

if __name__ == "__main__":
	started = False
	if not started:
		started = True
		go()


# from app import GUI
# from app import logSetup

# if __name__ == "__main__":
# 	logSetup.initLogging()
# 	# run()
# 	go()
