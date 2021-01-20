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
	remote_users: list

	def __init__(self, host, nick, port=64738, password=''):
		self.remote_users = []

		self.connection = pymumble3.Mumble(host, nick, port=port, password=password)
		self.connection.callbacks.set_callback(ON_TEXT, self.onText)
		self.connection.set_receive_sound(1)
		self.connection.start()
		self.connection.is_ready()

	def forAllOthers(self, f):
		for instance in instances:
			if instance != self:
				f(instance)

	def updateUserList(self):
		me = self.connection.users.myself
		if me is None: # this sometimes happens (during initialization?)
			return

		users = []
		self.forAllOthers(lambda x: users.extend(x.getUserNicks()))

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

	def getUserNicks(self):
		for user in self.getUsers():
			yield user['name']

	def getUsers(self):
		me = self.connection.users.myself
		for _, user in self.connection.users.items():
			if user['name'] != me['name'] and user['channel_id'] == me['channel_id']:
				yield user

	def onText(self, msg):
		sender = self.connection.users[msg.actor]
		self.forAllOthers(lambda x: x.transmitText("[{}]: {}".format(sender["name"], msg.message)))

	def transmitText(self, text):
		channel = self.connection.my_channel()
		channel.send_text_message(text)

	def sendAudioToOthers(self):
		pcm = None
		for user in self.getUsers():
			chunk = user.sound.get_sound(0.01)
			if chunk is None:
				continue

			userPcm = np.frombuffer(chunk.pcm, np.int16)
			if pcm is None:
				pcm = np.copy(userPcm)
			else:
				pcm += userPcm

		if pcm is not None:
			pcm = pcm.tobytes()
			self.forAllOthers(lambda x: x.connection.sound_output.add_sound(pcm))

def main():
	for host, port, nick in servers:
		print("connecting to {}:{} as {}".format(host, port, nick))
		instances.append(MumbleServerInstance(host, nick, port))

	i = 0
	while True:
		for instance in instances:
			instance.sendAudioToOthers()

		i += 1
		if i >= 100:
			for instance in instances:
				instance.updateUserList()
			i = 0

		time.sleep(0.005)

if __name__ == "__main__":
    main()
