
import visa
import time

rm = visa.ResourceManager('@py')
avail = rm.list_resources()
print(avail)
inst = rm.open_resource(avail[0], baud_rate = 9600)
inst.baud_rate = 9600
inst.timeout   = 2000
print(inst)

print(("response: ", inst.query("*IDN?")))
print(("response: ", inst.write("DIAG:MON 1")))
while 1:

	for cmd in ["CLOS", "OPEN"]:
		# for card in range(1,3):
		card = 2
		for s in range(3):
			cmd_s = '{mode} (@{card}0{s})'.format(mode=cmd, card=card, s=s)
			print(("Cmd: ", cmd_s, "response: ", inst.write(cmd_s)))
			time.sleep(0.05)
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