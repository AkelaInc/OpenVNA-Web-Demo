var vna_socket = io.connect('http://' + document.domain + ':' + location.port + "/vna_interface", {transports: ['websocket']});


function guid() {
	function s4() {
		return Math.floor((1 + Math.random()) * 0x10000)
			.toString(16)
			.substring(1);
	}
	return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
		s4() + '-' + s4() + s4() + s4();
}

// We need to be able to disambiguate between configuration
// packets we send, and other people's config update messages.
// Therefore, we generate a session GUID, and send that with
// all config updates.
// Then, when we receive broadcast configuration change messages,
// we check if they match our GUID, and if they do, ignore them
// so that we don't have annoying flicker issues when quickly
// updating the VNA settings
var local_GUID = guid();

var is_unlocked = false;


// We track the number of changes in the application pipeline, and
// show and hide a blurb depending on their status.
var pending_changes = 0;
var boxstate = "hidden";

var main_plot_options = {
	lines: {
		show: true
	},
	points: {
		show: false
	},
	xaxis: {axisLabel : 'Frequency (MHz)'},
	yaxis: {axisLabel: 'Magnitude (dB)', min:-90, max: 10},
	grid:
	{
		hoverable: true,
		autoHighlight: true
	},
};

var fft_plot_options = {
	lines: {
		show: true
	},
	points: {
		show: false
	},

	xaxis: {axisLabel : "Reflection Time (nanoseconds)"},
	yaxis: {axisLabel: 'Magnitude', min: 0, max: 0.12345},
	grid:
	{
		hoverable: true,
		autoHighlight: true
	},
};

function getMaxOfArray(numArray) {
	return Math.max.apply(null, numArray);
}
function getMinOfArray(numArray) {
	return Math.min.apply(null, numArray);
}

var running_fft_max = 0;


function bin_vna_data(raw_data)
{
	var data = msgpack.decode(raw_data)

	var fft_plot_data = [];
	var main_plot_data = [];

	if (data['pts'] && data['pts'].length > 0)
	{
		main_plot_data.push({label: "S11",  data: data['comp_data']['S11'], color: '#058DC7', yaxis : 1, xaxis: 1})
		main_plot_data.push({label: "S12",  data: data['comp_data']['S12'], color: '#AA4643', yaxis : 1, xaxis: 1})
		main_plot_data.push({label: "S21",  data: data['comp_data']['S21'], color: '#50B432', yaxis : 1, xaxis: 1})
		main_plot_data.push({label: "S22",  data: data['comp_data']['S22'], color: '#ED561B', yaxis : 1, xaxis: 1})
	}

	var max_fft = 0;

	if (data['fft_pts'] && data['fft_pts'].length > 0)
	{
		if (data['fft_data']['S11-FFT'] != undefined)
			max_fft = Math.max(max_fft, data['fft_max']['S11-FFT'])
		if (data['fft_data']['S12-FFT'] != undefined)
			max_fft = Math.max(max_fft, data['fft_max']['S12-FFT'])
		if (data['fft_data']['S21-FFT'] != undefined)
			max_fft = Math.max(max_fft, data['fft_max']['S21-FFT'])
		if (data['fft_data']['S22-FFT'] != undefined)
			max_fft = Math.max(max_fft, data['fft_max']['S22-FFT'])

		fft_plot_data.push({label: "S11 FFT",  data: data['fft_data']['S11-FFT'], color: '#058DC7', yaxis : 1, xaxis: 1})
		fft_plot_data.push({label: "S12 FFT",  data: data['fft_data']['S12-FFT'], color: '#AA4643', yaxis : 1, xaxis: 1})
		fft_plot_data.push({label: "S21 FFT",  data: data['fft_data']['S21-FFT'], color: '#50B432', yaxis : 1, xaxis: 1})
		fft_plot_data.push({label: "S22 FFT",  data: data['fft_data']['S22-FFT'], color: '#ED561B', yaxis : 1, xaxis: 1})


	}
	running_fft_max = Math.max(running_fft_max, max_fft)
	fft_plot_options['yaxis']['max'] = running_fft_max

	// states:
	//    - Main plot only
	//    - FFT Plot only
	//    - Main and FFT Plot
	//    - No plots

	var main_plt_div = $('#main_plot');
	var fft_plt_div  = $('#fft_plot');
	var no_plt_div   = $('#no_plot');

	var half_height = {"height" : "300px", "max-width" : "800px", "display" : ""}
	var full_height = {"height" : "600px", "max-width" : "800px", "display" : ""}
	var zero_height = {"height" : "0px",   "max-width" : "800px", "display" : "None"}

	if (main_plot_data.length > 0 && fft_plot_data.length > 0) // Both plots
	{
		main_plt_div.css(half_height)
		fft_plt_div.css(half_height)
		no_plt_div.css(zero_height)

	}
	else if (main_plot_data.length > 0) // Main plot only
	{
		main_plt_div.css(full_height)
		fft_plt_div.css(zero_height)
		no_plt_div.css(zero_height)

	}
	else if (fft_plot_data.length > 0)  // FFT Plot only
	{
		main_plt_div.css(zero_height)
		fft_plt_div.css(full_height)
		no_plt_div.css(zero_height)

	}
	else // No plots
	{
		main_plt_div.css(zero_height)
		fft_plt_div.css(zero_height)
		no_plt_div.css(full_height)

	}


	if (fft_plot_data.length)
		$.plot("#fft_plot", fft_plot_data, fft_plot_options);
	if (main_plot_data.length)
		$.plot("#main_plot", main_plot_data, main_plot_options);


	bouncebox_check_state();
	request_vna_data();

}

function bin_cam_data(data)
{
	var arrayBufferView = new Uint8Array( data );

	var blob = new Blob( [ arrayBufferView ], { type: "image/png" } );
	var urlCreator = window.URL || window.webkitURL;
	var imageUrl = urlCreator.createObjectURL( blob );

	// To avoid leaking blobs, we have to explicitly revoke the URL after the load has finished.
	// This also serves to limit the scope of the blob URLs to this function ONLY, which
	// prevents a mysterious refcount leak somewhere that was occuring when I was deferring
	// url revocation to the next call of `bin_cam_data()`.
	// When this wasn't done, we'd leak the image data continously, and leaving a browser open
	// for an hour or so would cause it to crash.
	$( "#main_cam" ).attr('src', imageUrl).load(function(){
		urlCreator.revokeObjectURL(imageUrl);
	});

	bouncebox_check_state();

	vna_socket.emit('bin data request', "cam plz");
}

function do_ui_update(data)
{

	// .prop('checked',true)

	if (data.hasOwnProperty('no-points'))
		$('#sweep-points').val(data['no-points']);
	if (data.hasOwnProperty('start-stop'))
	{
		$('#start-f').val(data['start-stop'][0]);
		$('#stop-f' ).val(data['start-stop'][1]);
	}

	if (data.hasOwnProperty('switch-matrix'))
	{
		for (var key in data['switch-matrix'])
		{
			if (data['switch-matrix'].hasOwnProperty(key))
			{
				var cb_obj = $('#'+key);
				var state  = data['switch-matrix'][key];
				// console.log("Matrix key: ", key, state)
				cb_obj.prop("checked", state);
			}
		}
	}

}

function update_interface(data)
{
	// Ignore update messages we ourselves generated.
	if (data['src-guid'] == local_GUID)
	{
		return;
	}
	else
	{
		do_ui_update(data)
	}
	bouncebox_external_change_notify();
}

function bouncebox_check_state()
{
	var box = $('#box');
	var header = $("#box.p.b");
	var text = $("#remaining_changes");

	if (!box.data('bounceShown') && pending_changes > 0)
	{
		header.html("Applying Changes")
		text.html(pending_changes.toString() + " remaining");
		box.clearQueue().bounceBoxShow();
	}
	if (box.data('bounceShown') && pending_changes == 0)
	{
		text.html(pending_changes.toString() + " remaining");
		box.clearQueue().bounceBoxHide()
	}

}

function bouncebox_external_change_notify()
{

	var box = $('#box');
	var header = $("#box.p.b");
	var text = $("#remaining_changes");

	header.html("Remote Change")
	text.html("Settings changed remotely!");

	// console.log("Remote change!");
	box.clearQueue().bounceBoxShow().delay(4000).bounceBoxHide();

}

function check_validate_numbers()
{
	if (Number($('#start-f').val()) + 1 > Number($('#stop-f').val()))
	{
		var num = Number($('#start-f').val()) + 1;
		$('#stop-f').val(num)
	}
	var nums = [$('#sweep-points'), $('#start-f'), $('#stop-f')]
	for (var i = 0; i < nums.length; i++)
	{

		var cur = Number(nums[i].val())
		var c_min = Number(nums[i].attr('min'))
		var c_max = Number(nums[i].attr('max'))

		if (cur < c_min)
			nums[i].val(c_min);
		if (cur > c_max)
			nums[i].val(c_max);
	}
	if (nums[1]+1 > nums[2])
		nums[2] = nums[1]+1
}


var vna_auth_msg = "Unfortunately, we don't have an infinite number of VNAs to put on the " +
				"internet. Therefore, we can't let everyone change the VNA settings at the " +
				"same time, as it would just result in confusion. As such, you need to ask " +
				"for permission to experiment with the VNA configuration yourself.";

function do_auth()
{
	var pass = $('#auth-password').val();
	vna_socket.emit('authenticate me plox', {
			"password"    : pass,
			"src-guid"    : local_GUID
		});
}

function get_password()
{


		bootbox.dialog({
				title: "Enter password for VNA control access:",
				message:
					'<div class="row">' +
					'	<div class="col-md-12">' +
					'		<div>' + vna_auth_msg +
					"			<br><br>If you have already contacted AKELA, please enter the unlock password below." +
					"		</div><br>" +
					'		<form class="form-horizontal" data-bb-handler="success">' +
					'			<div class="form-group">' +
					'				<label class="col-md-4 control-label" for="password">Password</label>' +
					'				<div class="col-md-4">' +
					'					<input id="auth-password" name="password" type="password" placeholder="Auth Password" class="form-control input-md">' +
					'				</div>' +
					'			</div>' +
					'		</form>' +
					'	</div>' +
					'</div>' +
					'<script type="text/javascript">$(document).on("submit", ".bootbox form", function(e) { e.preventDefault() });</script>'
					,
				buttons: {
					success: {
						label: "Unlock Controls",
						className: "btn-danger",
						callback: do_auth
						},
					main: {
						label: "Just watch for now!",
						className: "btn-primary pull-left",
						callback: function() {
							},
						},
					contact: {
						label: "Contact AKELA!",
						className: "btn-success pull-left",
						callback: function() {
							window.open("http://akelavna.com/contact.html");
						}
					}
				}
			}
		);

	// bootbox.prompt("Enter password for VNA control access:", function(result){

	// vna_socket.emit('authenticate me plox', {
	// 		"password"    : result,
	// 		"src-guid"    : local_GUID
	// 	});
	// })
}

function active_params_change()
{
	check_validate_numbers();
	var start = Number($('#start-f').val());
	var stop  = Number($('#stop-f').val());
	var npts = Number($('#sweep-points').val());

	var vals = {};
	$('.path-select').each(function(idx, val){
		var tmp = $( this );
		vals[tmp.attr("value")] = tmp.is(":checked");
	})

	pending_changes += 1;
	bouncebox_check_state();

	vna_socket.emit('config message', {
		"start-stop"    : [start, stop],
		"no-points"     : npts,
		"switch-matrix" : vals,
		"src-guid"      : local_GUID
	});

}

function reset_fft_running_max()
{
	running_fft_max = 0;
}


// -----------------------------------------------------------------------------------------------
//
// -----------------------------------------------------------------------------------------------

// The server works by emitting the new message for changes, and *then* a "change applied" message.
// Therefore, we simple listen for the change applied messages, and de-increment the count of applied
// changes when we see it.
function handle_applied_change(data)
{
	pending_changes -= 1;
	pending_changes = Math.max(pending_changes, 0)
}

function handle_unlock_message(data)
{
	$(".unlockable").prop('disabled', false);
	$("#auth_text").html('Full control');
	$("#authenticate_button_container").html('');

	is_unlocked = true;

	// console.log("Unlocking?")
}

function handle_error_message(data)
{
	bootbox.alert("Error:<br>"+data);
}

function update_active_users(data)
{

	$("#active-viewers").html(data[0]);
	$("#active-controllers").html(data[1]);
	// console.log("Active: ", data, data[0]);
}


function request_vna_data()
{
	var checks = {
			"S11"     : $('#sparam-s11').is(":checked"),
			"S12"     : $('#sparam-s12').is(":checked"),
			"S21"     : $('#sparam-s21').is(":checked"),
			"S22"     : $('#sparam-s22').is(":checked"),

			"S11-FFT" : $('#sparam-s11-fft').is(":checked"),
			"S12-FFT" : $('#sparam-s12-fft').is(":checked"),
			"S21-FFT" : $('#sparam-s21-fft').is(":checked"),
			"S22-FFT" : $('#sparam-s22-fft').is(":checked")
		};
	vna_socket.emit('bin data request', "vna plz", checks);

}

function update_cycle_state(data)
{
	console.log("update_cycle_state", data);
	var is_remote = data[0];
	if (is_remote)
	{
		if (is_unlocked)
			$("#experiment-timer").html("");
		else
			$("#experiment-timer").html("<br>Another user has direct control.<br>Auto-cycling disabled.");

		$("#take_control_text").html("");
	}
	else
	{
		var sago = data[1];
		var mins = Math.round(sago / 60)
		var secs = Math.round(sago % 60)
		// console.log(sago, mins, secs)
		$("#experiment-timer").html("<br>Cycling to next experiment in " + mins + "m, " + secs + "s.")
		$("#take_control_text").html("Take control to manually set active experiment.");
	}
}

// -----------------------------------------------------------------------------------------------
// Finally, attach all the events
// -----------------------------------------------------------------------------------------------

// Bind the listeners to the appropriate Socket.IO messages
// console.log("Attaching listeners");

vna_socket.on('bin_vna_data',   bin_vna_data);
vna_socket.on('bin_cam_data',   bin_cam_data);

vna_socket.on('config',         update_interface);

vna_socket.on('change_applied', handle_applied_change);
vna_socket.on('unlock',         handle_unlock_message);
vna_socket.on('error_message',  handle_error_message);

vna_socket.on('active',         update_active_users);
vna_socket.on('have_control',   update_cycle_state);


// Attach the change callbacks to the user-interface components
var number_opts = {"ro call" : get_password}

$('#sweep-points').bootstrapNumber(number_opts);
$('#start-f')     .bootstrapNumber(number_opts);
$('#stop-f')      .bootstrapNumber(number_opts);

$('#sweep-points').change(active_params_change);
$('#start-f')     .change(active_params_change);
$('#stop-f')      .change(active_params_change);


$('#sparam-s11-fft').click(reset_fft_running_max);
$('#sparam-s12-fft').click(reset_fft_running_max);
$('#sparam-s21-fft').click(reset_fft_running_max);
$('#sparam-s22-fft').click(reset_fft_running_max);

$('.path-select').change(active_params_change);

$('#authenticate_button').click(get_password);
$('#take_control_text').click(get_password);


// Finally, start the data fetching process by manually kicking off the data-request
// processes once the document is finished rendering.
$(document).ready(function() {
	request_vna_data();
	vna_socket.emit('bin data request', "cam plz");

	// Set up the notification box
	$('#box').bounceBox();
});


