import time
import numpy as np
import sys
from threading import Lock
import pymumble_py3 as pymumble3
from pymumble_py3.callbacks import \
	PYMUMBLE_CLBK_SOUNDRECEIVED as ON_SOUND, \
	PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as ON_TEXT, \
	PYMUMBLE_CLBK_DISCONNECTED as ON_DISCONNECT

servers = [
	# host, port, nickname
	("mumble.hopfenspace.org", 64738, "portal-to-neuland"),
	("voice.informatik.sexy", 64738, "portal-to-hopfenspace"),
]

instances = []

class MumbleServerInstance:
	mutex: Lock
	chunk_queue: list
	remote_users: list

	def __init__(self, host, nick, port=64738, password=''):
		self.mutex = Lock()
		self.chunk_queue = []
		self.remote_users = []

		self.connection = pymumble3.Mumble(host, nick, port=port, password=password)
		self.connection.callbacks.set_callback(ON_SOUND, self.onAudio)
		self.connection.callbacks.set_callback(ON_TEXT, self.onText)
		self.connection.callbacks.set_callback(ON_DISCONNECT, self.onDisconnect)
		self.connection.set_receive_sound(1)
		self.connection.start()
		self.connection.is_ready()
		self.connection.sound_output.set_audio_per_packet(0.02)

	def forAllOthers(self, f):
		for instance in instances:
			if instance != self:
				f(instance)

	def updateComment(self):
		me = self.connection.users.myself
		if me is None: # this sometimes happens (during initialization?)
			return

		users = []
		self.forAllOthers(lambda x: users.extend(x.getUsers()))

		if self.remote_users == users:
			return

		for user in users:
			if user not in self.remote_users:
				self.transmitText("* User {} joined".format(user))
		for user in self.remote_users:
			if user not in users:
				self.transmitText("* User {} left".format(user))

		self.remote_users = users

		if users:
			comment = "<strong>Users on the other side:</strong>"
			for user in users:
				comment += "<br>* {}".format(user)
		else:
			comment = "No users on the other side."

		me.comment(comment)

	def getUsers(self):
		me = self.connection.users.myself
		for _, user in self.connection.users.items():
			if user['name'] != me['name'] and user['channel_id'] == me['channel_id']:
				yield user['name']

	def onText(self, msg):
		sender = self.connection.users[msg.actor]
		self.forAllOthers(lambda x: x.transmitText("[{}]: {}".format(sender["name"], msg.message)))

	def transmitText(self, text):
		channel = self.connection.my_channel()
		channel.send_text_message(text)

	def addToQueue(self, stamp, pcm):
		self.mutex.acquire()

		for i, entry in enumerate(self.chunk_queue):
			if stamp == entry[0]:
				self.chunk_queue[i] = (stamp, np.add(entry[1], pcm))
				self.mutex.release()
				return
			elif stamp < entry[0]:
				pcm = np.copy(pcm)
				self.chunk_queue.insert(i, (stamp, pcm))
				self.mutex.release()
				return

		pcm = np.copy(pcm)
		self.chunk_queue.append((stamp, pcm))
		self.mutex.release()

	def onAudio(self, user, chunk):
		units = int(chunk.duration / 0.01)
		for i in range(units):
			part = chunk.extract_sound(0.01)
			stamp = int(part.time * 100)
			pcm = np.frombuffer(part.pcm, np.int16)
			self.forAllOthers(lambda x: x.addToQueue(stamp, pcm))

	def onDisconnect(self):
		sys.exit(1)

	def transmitAudio(self, stamp):
		self.mutex.acquire()

		if not self.chunk_queue:
			self.mutex.release()
			return

		curr, pcm = self.chunk_queue[0]
		first_stamp = curr
		last_stamp = curr
		transmit_count = 0
		while curr < stamp:
			self.chunk_queue.pop(0)
			self.connection.sound_output.add_sound(pcm.tobytes())
			transmit_count += 1

			if not self.chunk_queue:
				break
			curr, pcm = self.chunk_queue[0]
			last_stamp = curr

		self.mutex.release()


def main():
	for host, port, nick in servers:
		print("connecting to {}:{} as {}".format(host, port, nick))
		instances.append(MumbleServerInstance(host, nick, port))

	while True:
		stamp = int((time.time() - 0.1) * 100)
		for instance in instances:
			instance.transmitAudio(stamp)

		for instance in instances:
			instance.updateComment()

		time.sleep(0.05)

if __name__ == "__main__":
    main()
