
import multiprocessing
import time
import traceback
import logging
import signal
import cv2


class ThreadExit(Exception):
	pass

class CameraThread():
	def __init__(self, camera_id, command_queue, response_queue, exit_value):

		self.camera_id = camera_id
		self.log = logging.getLogger("Main.CAM-%s" % camera_id)

		self.exit_value = exit_value

		self.cap = cv2.VideoCapture(-1)
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

		self.command_queue  = command_queue
		self.response_queue = response_queue
		self.runstate       = False
		self.log.info("Camera Thread running")


	def dispatch(self, command):
		assert isinstance(command, tuple), "All commands must be a (command, params) tuple!"
		assert len(command) == 2, "All commands must be a (command, params) tuple!"

		command, params = command

		if command == "run":
			pass
		else:
			self.log.error("Unknown command: '%s'", command)
			self.log.error("Command parameters: '%s'", params)

	def process(self):
		ret, frame = self.cap.read()
		if ret:
			retval, buf = cv2.imencode(".png", frame)
			# print(buf)
			# print(buf.tostring())
			buf = buf.tostring()
			self.response_queue.put(("image", buf))

			# with app.app_context():
			# 	socketio.emit('cam data', ("image", imstr), namespace='/vna_interface')

			# Limit queue size to 10 items.
			#
			while self.response_queue.qsize() > 30:
				print("truncating queue")
				tmp = self.response_queue.get()
				if tmp[0] != "image":
					self.response_queue.put(tmp)
		else:
			print("failure opening camera?")
			return True


		return False

	def run(self):
		try:
			while self.exit_value.value:
				try:
					if self.process():
						time.sleep(0.333333)
				except Exception:
					self.log.error("Exception in camera interface thread!")
					traceback.print_exc()
		except ThreadExit:
			self.log.info("Thread halting")
		self.shutdown()

	def shutdown(self):
		pass

def threadProcess(cam_id, command_queue, response_queue, exit_value):
	camt = CameraThread(cam_id, command_queue, response_queue, exit_value)

	# Ignore ctrl+c events
	signal.signal(signal.SIGINT, signal.SIG_IGN)

	camt.run()
	print("Camera Thread exited")

def create_thread(cam_id, command_queue, response_queue, exit_value):
	proc = multiprocessing.Process(target=threadProcess, args=(cam_id, command_queue, response_queue, exit_value))
	proc.start()
	return proc

