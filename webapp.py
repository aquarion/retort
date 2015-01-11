# This is Retort, a thing to boil iKettles in Flask.
# It is built on the shoulders of giants.
#
# This is the flask app. It's got no complicated bits
#
# things to do: 
#    Move API bits to flask-restful
#	 Add a GUI
#    Add a pretty GUI
#    WebSockets for GUI updates? I heard you like sockets, so I put sockets in your sockets
#    Save value for IP
#
# Nicholas 'Aquarion' Avenell 2015

from flask import Flask

from kettle import Kettle

app = Flask(__name__)

kettle = Kettle(False, False)

@app.route('/')
@app.route('/index')
def index():
	kettle.update_status()
	return "%s" % kettle.current_status()

@app.route('/stop')
def stop():
	kettle.update_status()
	kettle.stopboil()
	return "Hello World"

@app.route('/start')
def start():
	kettle.clickboil()
	return "Hello World"

@app.route('/temp/<temperature>')
def temp(temperature):
	kettle.set_temp(temperature)
	return "Hello World"

app.run(debug=True)