
def CONNECT(slot, fnc):
	slot.get().append(fnc)

def DISCONNECT(slot, fnc):
	slot.get().remove(fnc)

