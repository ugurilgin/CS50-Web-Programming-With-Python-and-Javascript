import os
import time

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, send, join_room, leave_room
from flask_session import Session

# set up Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode = None)

# keep track of the users, channels and the messages in each channel
channels = []
my_messages = {}
users = {}



@socketio.on("username")
def receive_username(username):
	# pair usernames with session IDs
	users[username] = request.sid

# execute when a message is sent
@socketio.on("room_message")
def messageHandler(json):
	# grab the timestamp for when the message was sent
	my_time = time.ctime(time.time())
	# organize the data into a dict
	my_data ={"user": json["user"], "msg" : json["msg"], "my_time": my_time}
	# add data to the messages of the channel in question
	my_messages[json["channel"]].append(my_data)
	# store only the 100 most recent messages per channel
	if len(my_messages[json["channel"]]) > 100:
		my_messages[json["channel"]].pop(0)
	# send back the time, the message and the username to the client side
	print("Message passed on!")
	emit("room_message", my_data, room = json["channel"])

# execute when the user tries to create a channel
@socketio.on("channel_creation")
def channel_creation(channel):
	# channel name is taken
	if channel in channels:
		emit("channel_error", "This name is already taken!")
	# success
	else:
		# add channel to the list of channels
		channels.append(channel)
		my_messages[channel] = []
		# add user to the channel
		join_room(channel)
		current_channel = channel
		data = {"channel": channel, "messages": my_messages[channel]}
		emit("join_channel", data)

# execute when the user joins a channel
@socketio.on("join_channel")
def join_channel(channel):
	# add user to the channel
	join_room(channel)
	data = {"channel": channel, "messages": my_messages[channel]}
	print(data)
	emit("join_channel", data)

# execute when the user leaves the channel they are on
@socketio.on("leave_channel")
def leave_channel(channel):
	# remove user from the channel
	leave_room(channel)
	emit("leave_channel", channel)

# execute when the user changes channels
@socketio.on("change_channel")
def change_channel(old_channel, new_channel):
	# remove user from the old channel
	leave_room(old_channel)
	# add user to the new channel
	join_room(new_channel)
	data = {"channel": new_channel, "messages": my_messages[new_channel]}
	emit("join_channel", data)

@app.route("/")
def index():
	# return the main page
	return render_template("index.html", channels = channels, users = users, async_mode = socketio.async_mode)

if __name__ == "__main__":
	socketio.run(app, debug = True)
