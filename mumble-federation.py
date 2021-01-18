import time
import numpy as np
from threading import Lock
import pymumble_py3 as pymumble3
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED as PCS

servers = [
	# host, port, nickname
	("hopfenspace.org", 64738, "portal-to-neuland"),
	("informatik.sexy", 64738, "portal-to-hopfenspace"),
]

mutex = Lock()
connections = []
chunks = [None for _ in servers]
locks = [Lock() for _ in servers]

def onAudioClosure(receiver, name):
	def onAudio(user, chunk):
		for i, conn in enumerate(connections):
			if conn == receiver:
				continue

			pcm = np.frombuffer(chunk.pcm, np.int16)

			locks[i].acquire()
			if chunks[i] is None:
				chunks[i] = pcm
			else:
				chunks[i] = np.add(chunks[i], pcm)
			locks[i].release()

	return onAudio

for host, port, nick in servers:
	print("connecting to {}:{} as {}".format(host, port, nick))
	conn = pymumble3.Mumble(host, nick, port=port)
	conn.callbacks.set_callback(PCS, onAudioClosure(conn, "{}:{}".format(host, port)))
	conn.set_receive_sound(1)
	conn.start()
	conn.is_ready()

	connections.append(conn)

while True:
	for i, conn in enumerate(connections):
		locks[i].acquire()
		if chunks[i] is not None:
			conn.sound_output.add_sound(chunks[i].tobytes())
			chunks[i] = None
		locks[i].release()
	time.sleep(0.02)
