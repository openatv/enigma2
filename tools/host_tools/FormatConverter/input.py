import sys


def inputText():
	input = sys.stdin.readline()
	return input.strip()


def inputChoices(list, backcmd="b", backtext="back"):
	repeat = True
	while repeat:
		repeat = False
		count = 0
		for item in list:
			print count, "-", item
			count += 1
		print backcmd, "-", backtext
		input = inputText()
		if input == backcmd:
			return None

		action = int(input)
		if action >= len(list):
			repeat = True
	return action
