import time
import numpy as np
from threading import Lock
import pymumble_py3 as pymumble3
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED as PCS

servers = [
	# host, port, nickname
	("hopfenspace.org", 64738, "dev-portal-to-neuland"),
	("informatik.sexy", 64738, "dev-portal-to-hopfenspace"),
]

instances = []

class MumbleServerInstance:
	mutex: Lock
	chunk: np.array

	def __init__(self, host, nick, port=64738, password=''):
		self.mutex = Lock()
		self.chunk = None

		self.connection = pymumble3.Mumble(host, nick, port=port)
		self.connection.callbacks.set_callback(PCS, self.onAudio)
		self.connection.set_receive_sound(1)
		self.connection.start()
		self.connection.is_ready()

	def onAudio(self, user, chunk):
		pcm = np.frombuffer(chunk.pcm, np.int16)

		for instance in instances:
			if instance != self:
				instance.addAudioSignal(pcm)

	def addAudioSignal(self, pcm):
		self.mutex.acquire()
		if self.chunk is None:
			self.chunk = np.copy(pcm)
		else:
			self.chunk += pcm
		self.mutex.release()

	def transmitAudio(self):
		self.mutex.acquire()
		if self.chunk is not None:
			self.connection.sound_output.add_sound(self.chunk.tobytes())
			self.chunk = None
		self.mutex.release()

def main():
	for host, port, nick in servers:
		print("connecting to {}:{} as {}".format(host, port, nick))
		instances.append(MumbleServerInstance(host, nick, port))

	while True:
		for instance in instances:
			instance.transmitAudio()
		time.sleep(0.02)

if __name__ == "__main__":
    main()
