
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

#############################################################################
# Shared-state messyness for the borg classes

class Borg_Hardware(object):
	_shared_state = {"initialized" : False}
	def __init__(self):
		self.__dict__ = self._shared_state

class Borg_Login(object):
	_shared_state = {"initialized" : False}
	def __init__(self):
		self.__dict__ = self._shared_state

#############################################################################

class HardwareArbiter(Borg_Hardware):
	def __init__(self):
		super().__init__()
		if not self.initialized:
			self.__initialize()

	def __initialize(self):
		self.log = logging.getLogger("Main.Arbiter")
		self.log.info("Initializaing system processes")

		self.shared_exit_flag = multiprocessing.Value("i")
		self.shared_exit_flag.value = 1

		self.cam_command_queue  = multiprocessing.Queue()
		self.cam_response_queue = multiprocessing.Queue()

		self.vna_command_queue  = multiprocessing.Queue()
		self.vna_response_queue = multiprocessing.Queue()

		self.visa_command_queue  = multiprocessing.Queue()
		self.visa_response_queue = multiprocessing.Queue()

		self.bk_thread_v = vnat.create_thread(0, self.vna_command_queue,  self.vna_response_queue,  self.shared_exit_flag)
		self.bk_thread_c = camt.create_thread(0, self.cam_command_queue,  self.cam_response_queue,  self.shared_exit_flag)
		self.bk_thread_s = snat.create_thread(   self.visa_command_queue, self.visa_response_queue, self.shared_exit_flag)

		self.vna_command_queue.put(("connect", (config.VNA_IP, config.VNA_PORT)))
		self.vna_command_queue.put(("run", True))

		self.run              = True
		self.processes_exited = False

		self.lock = rwlock.RWLock()

		self.image    = None
		self.vna_data = None

		self.startf     = config.VNA_STARTF
		self.stopf      = config.VNA_STOPF
		self.experiment = config.VNA_EXPERIMENT
		self.npts       = config.VNA_NPTS


		self.q_thread = threading.Thread(target=self.__process)
		self.q_thread.start()


	def get_acq_conf(self):
		with self.lock.reader_context():
			ret = {
				"startf" : self.startf,
				"stopf"  : self.stopf,
				"path"   : self.experiment,
				"npts"   : self.npts,
			}
		return ret

	def set_num_points(self, npts):
		with self.lock.writer_context():
			self.npts = npts
		self.send_vna_command(("npts", npts))


	def set_start_stop_freq(self, start, stop):
		with self.lock.writer_context():
			self.startf = start
			self.stopf  = stop
		self.send_vna_command(("start-stop", (start, stop)))


	def set_experiment(self, experiment_dict):
		self.log.info("Setting experiment to %s", experiment_dict)
		if not "experiment-4" in experiment_dict:
			experiment_dict["experiment-4"] = False
		with self.lock.writer_context():
			self.experiment = experiment_dict
		self.send_visa_command(("switches", experiment_dict))

	def close(self):
		self.run = False
		self.log.info("Telling hardware processes to exit")
		self.visa_command_queue.put(("exit", True))
		self.shared_exit_flag.value = 0
		self.log.info("Waiting on processes halting.")
		self.bk_thread_v.join()
		self.bk_thread_c.join()
		self.bk_thread_s.join()
		self.log.info("Background processes exited.")
		self.processes_exited = True
		self.q_thread.join()
		self.log.info("Queue processor thread exited.")

	def get_image(self):
		with self.lock.reader_context():
			return copy.deepcopy(self.image)

	def get_vna_data(self):
		with self.lock.reader_context():
			return copy.deepcopy(self.vna_data)


	def send_visa_command(self, command):
		self.visa_command_queue.put(command)

	def send_vna_command(self, command):
		self.vna_command_queue.put(command)

	def send_cam_command(self, command):
		self.cam_command_queue.put(command)

	def __image_update(self):
		try:
			new = self.cam_response_queue.get_nowait()
		except queue.Empty:
			return

		if self.cam_response_queue.qsize() > 10:
			print("WARNING: Cam queueSize appears to be bloating up!")


		assert len(new) == 2, "Invalid number of items in image response object! ('%s')" % new

		mode, data = new
		if mode == "image":
			with self.lock.writer_context():
				self.image = data
		else:
			print("(CAM) Unknown mode: '%s'" % mode)

	def __vna_update(self):
		new = None
		try:
			while self.vna_response_queue.qsize():
				new = self.vna_response_queue.get_nowait()
		except queue.Empty:
			pass

		if new is None:
			return

		assert len(new) == 2, "Invalid number of items in VNA response object! ('%s')" % new

		mode, data = new
		if mode == "sweep data":
			with self.lock.writer_context():
				self.vna_data = data
		else:
			print("(VNA) Unknown mode: '%s'" % mode)


	def __update_from_queues(self):
		self.__image_update()
		self.__vna_update()

	def __process(self):
		while self.run:
			self.__update_from_queues()
			time.sleep(0.05)

		# While we're shutting down, we have to make sure all the queues are empty,
		# or their thread in the separate processes will never join, and we'll get
		# a hang. As such, spin on emptying items from the queues
		# until the child-threads finally exit.
		while self.processes_exited == False:
			queues_to_flush = [self.cam_command_queue, self.cam_response_queue, self.vna_command_queue, self.vna_response_queue]
			for t_queue in queues_to_flush:
				try:
					t_queue.get_nowait()
				except queue.Empty:
					pass
			time.sleep(0.333)
			print("self.processes_exited", self.processes_exited)


class LoginArbiter(Borg_Login):
	def __init__(self):
		super().__init__()
		if not self.initialized:
			self.__initialize()

	def __initialize(self):
		self.log = logging.getLogger("Main.LoginArbiter")
		self.log.info("Initializing login manager")

		self.lock = threading.Lock()
		self.authenticatedUsers = set()
		self.activeUsers = set()

	def __active_unlocked(self):
		active = len(self.activeUsers)
		authed = len(self.authenticatedUsers)
		assert active >= authed
		active -= authed
		return active, authed

	def active_clients(self):
		with self.lock:
			return self.__active_unlocked()

	def anyone_controlling(self):
		with self.lock:
			return bool(self.__active_unlocked()[1])

	def add_non_auth(self, sid):
		with self.lock:
			self.activeUsers.add(sid)
			return self.__active_unlocked()

	def remove_item(self, sid):
		with self.lock:
			self.activeUsers.discard(sid)
			self.authenticatedUsers.discard(sid)
			return self.__active_unlocked()

	def check_auth(self, guid):
		with self.lock:
			return guid in self.authenticatedUsers

	def add_auth_guid(self, guid):
		with self.lock:
			self.authenticatedUsers.add(guid)
			return self.__active_unlocked()

	def get_passwords(self):

		with open("passwords.txt", "r") as fp:
			passwords = fp.readlines()

		passwords = [passwd.strip() for passwd in passwords]
		return passwords