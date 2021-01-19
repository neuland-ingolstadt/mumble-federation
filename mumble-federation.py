import time
import numpy as np
from threading import Lock
import pymumble_py3 as pymumble3
from pymumble_py3.callbacks import \
	PYMUMBLE_CLBK_SOUNDRECEIVED as ON_SOUND, \
	PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as ON_TEXT

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
		self.connection.callbacks.set_callback(ON_SOUND, self.onAudio)
		self.connection.callbacks.set_callback(ON_TEXT, self.onText)
		self.connection.set_receive_sound(1)
		self.connection.start()
		self.connection.is_ready()

	def forAllOthers(self, f):
		for instance in instances:
			if instance != self:
				f(instance)

	def onText(self, msg):
		sender = self.connection.users[msg.actor]
		self.forAllOthers(lambda x: x.transmitText("[{}]: {}".format(sender["name"], msg.message)))

	def transmitText(self, text):
		channel = self.connection.my_channel()
		channel.send_text_message(text)

	def onAudio(self, user, chunk):
		pcm = np.frombuffer(chunk.pcm, np.int16)
		self.forAllOthers(lambda x: x.addAudioSignal(pcm))

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
