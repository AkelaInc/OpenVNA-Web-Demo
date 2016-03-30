
import multiprocessing
import time
import traceback
import logging
import signal

import visa
import queue
import serial
import config
import pyfirmata


LED_MAP = {
	1 : 4,
	2 : 1,
	3 : 3,
	4 : 2,
}

SWITCH_MAP = {
	1 : 1,
	2 : 2,
	3 : 3,
	4 : 4,
}

class ThreadExit(Exception):
	pass

class SwitchThread():
	def __init__(self, command_queue, response_queue, exit_value):


		self.rm = visa.ResourceManager('@py')
		avail = self.rm.list_resources()
		print("Available VISA resources: ", avail)
		valid_port = None
		for x in range(len(avail)):
			try:
				inst_tmp = self.rm.open_resource(avail[x], baud_rate = 9600)
				inst_tmp.baud_rate = 9600
				inst_tmp.timeout   = 2000

				model_info = inst_tmp.query("*IDN?")
				if "Agilent Technologies,3499" in model_info:
					print("Found HP Switchbox on port {}".format(x))
					valid_port = x
					break
			except serial.SerialException:
				pass

		if valid_port is None:
			raise IOError ("Cannot find HP 3499 switch-box!")

		self.log = logging.getLogger("Main.SW-%s" % valid_port)


		self.inst = self.rm.open_resource(avail[valid_port], baud_rate = 9600)
		self.inst.baud_rate = 9600
		self.inst.timeout   = 2000
		model_info = self.inst.query("*IDN?")

		assert 'Agilent Technologies,3499' in model_info, "The visa id %s must point to a Agilent 3499 switch controller. Returned device ID: %s" % (valid_port, model_info)

		self.log.info("VISA Device %s corresponds to device '%s'", valid_port, model_info)


		self.led_board = pyfirmata.Arduino(config.ARDUINO_COM_PORT)


		self.exit_value = exit_value

		self.command_queue  = command_queue
		self.response_queue = response_queue
		self.runstate       = False
		self.log.info("VISA Switchbox Thread running")

		self.active_experiment = config.VNA_EXPERIMENT

		self.switch_states = {}

	def set_state(self, plane, s, state):
		# state = "OPEN" if state else "CLOS"
		cmd_s = '{mode} (@{card}0{s})'.format(mode=state, card=plane, s=s)
		self.log.info("Switch command: '%s', response: '%s'", cmd_s, self.inst.write(cmd_s))


	def get_or_have(self, plane, x, y):
		# Get the value of switch plane:x:y.
		# Return boolan True/False if it's present, None
		# if it's missing

		if not plane in self.switch_states:
			self.switch_states[plane] = {}
		if not x in self.switch_states[plane]:
			self.switch_states[plane][x] = {}
		if not y in self.switch_states[plane][x]:
			return None
		return self.switch_states[plane][x][y]


	def set_active_experiment(self, experiment):
		'''

		The experiment wiring layout looks like the following:

		                Switch Plane 1

		                            o-------.
		                      .-o--__ SW 0  |
		                   o--'     o-------)-------.
		           .---o--__                |       |
		           |       o--.     o-------)-------)-------.
		  .-----.  |  SW 1    '-o--__ SW 2  |       |       |
		  | VNA |  |                o-------)-------)-------)-------.
		  |     |  |                     .--o--. .--o--. .--o--. .--o--.
		  |  o--)--'                     |     | |     | |     | |     |
		  |     |                        | EXP | | EXP | | EXP | | EXP |
		  |     |                        |  1  | |  2  | |  3  | |  4  |
		  |  o--)--.                     |     | |     | |     | |     |
		  |     |  |                     '--o--' '--o--' '--o--' '--o--'
		  |     |  |                o-------'       |       |       |
		  '-----'  |          .-o--__ SW 0          |       |       |
		           |       o- '     o---------------'       |       |
		           '---o--__                                |       |
		                   o- .     o-----------------------'       |
		              SW 1    '-o--__ SW 2                          |
		                            o-------------------------------'

		               Switch Plane 2


		As such, switch plane 1 and 2 must be switched together.

		The active experiment is a function of switch 1&0, or 1&2 depending
		on switch 1's state.

		Switches have port 0 as Normally-open, port 1 as normally closed.
		Therefore, if sw 1 and sw 0 are closed, experiment 1 /should/ be
		selected. If sw 1 is closed and sw 0 is open, experiment 2 should
		be selected, and as logically follows for experiment 3 and 4
		'''

		if experiment not in [1, 2, 3, 4]:
			self.log.error("Unknown experiment: %s", experiment)
			return

		led_num = LED_MAP[experiment]
		switch_num = SWITCH_MAP[experiment]

		self.log.info("Setting active experiment to %s (LED: %s, switch = %s)", experiment, led_num, switch_num)

		self.led_board.digital[13].write(1)
		self.led_board.digital[12].write(led_num == 1)
		self.led_board.digital[11].write(led_num == 2)
		self.led_board.digital[10].write(led_num == 3)
		self.led_board.digital[ 9].write(led_num == 4)

		for switch_plane in range(1,3):
			if switch_num == 1:
				self.set_state(switch_plane, 0, "CLOS")
				self.set_state(switch_plane, 1, "CLOS")
			elif switch_num == 2:
				self.set_state(switch_plane, 0, "OPEN")
				self.set_state(switch_plane, 1, "CLOS")
			elif switch_num == 3:
				self.set_state(switch_plane, 2, "OPEN")
				self.set_state(switch_plane, 1, "OPEN")
			elif switch_num == 4:
				self.set_state(switch_plane, 2, "CLOS")
				self.set_state(switch_plane, 1, "OPEN")

		self.led_board.digital[13].write(0)

	def process_switch_set(self, params):

		active = []
		for switch, state in params.items():
			if state:
				active.append(switch.split("-")[-1])
		if len(active) == 1:
			experiment = int(active.pop())
			self.set_active_experiment(experiment)


	def dispatch(self, command):
		assert isinstance(command, tuple), "All commands must be a (command, params) tuple!"
		assert len(command) == 2, "All commands must be a (command, params) tuple!"

		command, params = command

		if command == "run":
			pass
		elif command == "switches":
			if isinstance(params, dict):
				self.process_switch_set(params)
		elif command == "exit":
			if params is True:
				raise ThreadExit("Shutting down")
		else:
			self.log.error("Unknown command: '%s'", command)
			self.log.error("Command parameters: '%s'", params)

	def process(self):

		try:
			command = self.command_queue.get()
			self.dispatch(command)
			return False
		except queue.Empty:
			print("Queue empty")
			return True     # Queue is empty, sleep for a bit.


	def run(self):
		while self.exit_value.value:
			try:
				if self.process():
					time.sleep(0.05)
			except ThreadExit:
				self.log.info("Thread exit event")
				break
			except Exception:
				self.log.error("Exception in VISA interface thread!")
				traceback.print_exc()
		self.log.info("Thread halting")
		self.shutdown()

	def shutdown(self):
		pass

def threadProcess(command_queue, response_queue, exit_value):
	camt = SwitchThread(command_queue, response_queue, exit_value)

	# Ignore ctrl+c events
	signal.signal(signal.SIGINT, signal.SIG_IGN)

	camt.run()
	print("VISA Thread exited")

def create_thread(command_queue, response_queue, exit_value):
	proc = multiprocessing.Process(target=threadProcess, args=(command_queue, response_queue, exit_value))
	proc.start()
	return proc


