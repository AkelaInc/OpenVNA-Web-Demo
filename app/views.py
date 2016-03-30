
import msgpack
import traceback

from flask import render_template
from flask import request
from flask import send_from_directory
from flask_socketio import emit

import os.path
import logging

# from guess_language import guess_language
from app import app
from app import socketio
import json


log = logging.getLogger("Main.Web")


def error_response(err_str):
	emit('error_message', "Error processing request: {}".format(err_str), namespace='/vna_interface')


@app.after_request
def after_request(response):
	# print("After request call!", response)
	return response

@app.errorhandler(404)
def not_found_error(dummy_error):
	log.error("404. Wat: {}".format(dummy_error))
	return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(dummy_error):
	log.error("Internal Error!")
	log.error(dummy_error)
	log.error(traceback.format_exc())
	return render_template('500.html'), 500

@app.route('/favicon.ico')
def favicon():
	path = os.path.join(app.root_path, 'static', 'img')
	log.info("Sending from: '%s'", path)
	return send_from_directory(path, 'Akela_Logo.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
	return render_template('index.html',
						   title               = 'Home',
						   acq_params          = app.config['ARBITER'].get_acq_conf(),
						   active_users        = app.config['LOGIN_ARBITER'].active_clients(),
						   )


@app.route('/docs', methods=['GET'])
def docs():
	return render_template('docs.html')

@app.route('/your_experiment', methods=['GET'])
def your_experiment():
	return render_template('your_experiment.html')

@socketio.on('config message', namespace='/vna_interface')
def config_change(data):

	if not isinstance(data, dict):
		raise ValueError("Wat?")

	if not 'src-guid' in data:
		error_response("That doesn't work without a source GUID!")
		return

	if not app.config['LOGIN_ARBITER'].check_auth(request.sid):
		error_response("You have to be authenticated to do that. Nice try, though!")
		return

	# Re-broadcast change so all clients can pick it up.
	# emit('config update', data, broadcast=True)
	emit('config', data, broadcast=True, namespace='/vna_interface')

	# def set_num_points(self, npts):
	# def set_start_stop_freq(self, start, stop):
	# def set_experiment(self, experiment_num):

	if 'no-points' in data:
		print("Point number:", data['no-points'])

		app.config['ARBITER'].set_num_points(data['no-points'])

	if 'start-stop' in data:
		app.config['ARBITER'].set_start_stop_freq(*data['start-stop'])

	if 'switch-matrix' in data:
		app.config['ARBITER'].set_experiment(data['switch-matrix'])


	emit('change_applied', "config change OK", namespace='/vna_interface')


def extract_requested_data(want_data):

	# Valid keys for normal and FFT measurements
	norm_arrs = ['S12',     'S11',     'S21',     'S22'    ]
	fft_arrs  = ['S11-FFT', 'S21-FFT', 'S22-FFT', 'S12-FFT']

	vna_dat = app.config['ARBITER'].get_vna_data()

	# Pull out only true keys
	requested = [key for key in want_data.keys() if want_data[key]]

	# And mask for validity
	requested = [key for key in requested if key in fft_arrs+norm_arrs]

	want_norm = any([key in norm_arrs for key in requested])
	want_fft  = any([key in fft_arrs  for key in requested])

	for path in [key for key in norm_arrs if not key in requested]:
		del vna_dat['comp_data'][path]

	for path in [key for key in fft_arrs if not key in requested]:
		del vna_dat['fft_data'][path]

	if not want_fft:
		vna_dat['fft_pts'] = None
		vna_dat['fft_data'] = None

	if not want_norm:
		vna_dat['pts'] = None
		vna_dat['comp_data'] = None

	return vna_dat

@socketio.on('bin data request', namespace='/vna_interface')
def binary_data_request(message, data=None):
	if message == "vna plz":
		if not data:
			print("Wat?")
			return

		try:
			vna_dat = extract_requested_data(data)

			emit('bin_vna_data', msgpack.packb(vna_dat), namespace='/vna_interface')
		except TypeError:
			log.error("Error when extracting data?")
			for line in traceback.format_exc().split("\n"):
				log.error(line)

			error_response("Encountered an error fetching data. Pleas reload the page!")


	elif  message == "cam plz":
		emit('bin_cam_data', app.config['ARBITER'].get_image(), namespace='/vna_interface')
	else:
		error_response("Wat? Unknown data type request: '%s'" % message)

@socketio.on('authenticate me plox', namespace='/vna_interface')
def authenticate_message(msg):
	if not "password" in msg and "src-guid" in msg:
		error_response("Invalid authentication message!")
		return

	if not (msg['src-guid'] and msg['password']):
		error_response("Password/GUID cannot be empty!")
		return

	passwords = app.config['LOGIN_ARBITER'].get_passwords()
	received_pass = msg['password'].strip()
	if received_pass in passwords:
		print("User autheticated successfully!")
		active = app.config['LOGIN_ARBITER'].add_auth_guid(request.sid)
		emit('unlock', "true", namespace='/vna_interface')
		emit('active', list(active), broadcast=True, namespace='/vna_interface')
	else:
		error_response("Invalid Password!")

@socketio.on('connect', namespace='/vna_interface')
def event_connect():
	log.info("event_connect() -> %s", request.sid)
	active = app.config['LOGIN_ARBITER'].add_non_auth(request.sid)
	if active[0]:
		emit('active', list(active), broadcast=True, namespace='/vna_interface')

@socketio.on('disconnect', namespace='/vna_interface')
def event_disconnect():
	log.info("event_disconnect() -> %s", request.sid)
	active = app.config['LOGIN_ARBITER'].remove_item(request.sid)
	if active[0] or active[1]:
		emit('active', list(active), broadcast=True, namespace='/vna_interface', include_self=False)

@socketio.on_error()        # Handles the default namespace
def error_handler(e):
	print(e)

