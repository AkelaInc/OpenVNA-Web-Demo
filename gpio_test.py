
import visa
import time


from pyfirmata import Arduino, util

board = Arduino('/dev/ttyACM0')

led_pin = board.digital[13]

while True:
    led_pin.write(1)
    time.sleep(1)
    led_pin.write(0)
    time.sleep(1)

	# print(("response: ", inst.write('OPEN (@100)')))

	# print(("response: ", inst.write('CLOS (@101)')))
	# time.sleep(0.001)
	# print(("response: ", inst.write('OPEN (@101)')))
	# time.sleep(0.001)
	# print(("response: ", inst.write('CLOS (@101)')))
	# time.sleep(0.001)
	# print(("response: ", inst.write('OPEN (@101)')))
	# time.sleep(0.001)
	# print(("response: ", inst.write('CLOS (@101)')))
	# time.sleep(0.001)
	# print(("response: ", inst.write('OPEN (@101)')))
	# time.sleep(0.05)
	# print(("response: ", inst.write('CLOS (@102)')))
	# time.sleep(0.25)
	# print(("response: ", inst.write('CLOS (@103)')))
	# time.sleep(0.05)

	# print(("response: ", inst.write('CLOS (@110)')))
	# time.sleep(0.05)
	# print(("response: ", inst.write('CLOS (@120)')))
	# time.sleep(0.05)
	# print(("response: ", inst.write('CLOS (@130)')))
	# time.sleep(0.05)

	# # print(("response: ", inst.write('CLOS (@104)')))
	# # time.sleep(0.05)

	# print(("response: ", inst.write('OPEN (@101,102,103)')))
	# time.sleep(0.1)
	# print(("response: ", inst.write('OPEN (@110,120,130)')))
	# time.sleep(0.5)
# print(("response: ", inst.write("SYST:CPON 1")))