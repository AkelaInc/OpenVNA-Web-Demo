
try:
	import logSetup
	logSetup.initLogging()
except:
	print("No logging!")
	import traceback
	traceback.print_exc()


import time



import copy
import multiprocessing
import threading
import logging
import time
import queue
import app.camthread    as camt
import app.vnathread    as vnat
import app.switchthread as snat

import config
import rwlock

def go():

	print("Starting background threads")

	shared_exit_flag = multiprocessing.Value("i")
	shared_exit_flag.value = 1

	vna_command_queue  = multiprocessing.Queue()
	vna_response_queue = multiprocessing.Queue()

	bk_thread_v = vnat.create_thread(0, vna_command_queue,  vna_response_queue, shared_exit_flag)
	vna_command_queue.put(("connect", ("192.168.1.207", 1025)))
	vna_command_queue.put(("run", True))

	sweeps = 0

	try:
		print("Entering main run-loop")
		while 1:
			dum = vna_response_queue.get()
	except KeyboardInterrupt:
		pass

	run = False
	print("Telling hardware processes to exit")
	shared_exit_flag.value = 0
	print("Waiting on processes halting.")
	bk_thread_v.join()

	print("Threads halted. App exiting.")

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
