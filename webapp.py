# This is Retort, a thing to boil iKettles in Flask.
# It is built on the shoulders of giants.
#
# This is the flask app. It's got no complicated bits
#
# things to do: 
#    Move API bits to flask-restful
#    Add a pretty GUI
#    WebSockets for GUI updates? I heard you like sockets, so I put sockets in your sockets
#
# Nicholas 'Aquarion' Avenell 2015

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from kettle import Kettle

from alexa_cxn import AlexaRequest, AlexaResponse

import time
import logging
logger = logging.getLogger("Retort")
logger.propagate = False

from systemd.journal import JournaldLogHandler

logger.addHandler(JournaldLogHandler())
logger.setLevel(logging.WARNING)

logging.basicConfig(level=logging.WARNING)


app = Flask(__name__)

kettle = Kettle()

def something_changed():
     print "Kettle Start %s" % kettle

kettle.events.kettle_start += something_changed

@app.route('/')
def index():
	return render_template('index.html', kettle=kettle.latest_status())

@app.route('/status')
def status():
	logging.info("> REQUEST: Getting status")
	return jsonify(kettle.latest_status())

@app.route('/stop')
def stop():
	logging.info("> REQUEST: Stopping")
	kettle.latest_status()
	kettle.stopboil()
	return jsonify(kettle.current_status())

@app.route('/start')
def start():
	logging.info("> REQUEST: Starting")
	kettle.clickboil()
	return jsonify(kettle.current_status())

@app.route('/warm')
def warm():
	logging.info("> REQUEST: Toggle Warm")
	kettle.togglewarm()
	return jsonify(kettle.current_status())

@app.route('/temp/<temperature>')
def temp(temperature):
	logging.info("> REQUEST: Setting temperature to %s" % temperature)
	kettle.set_temp(temperature)
	return jsonify(kettle.current_status())


@app.route('/alexa', methods=['GET', 'POST'])
def alexa():
	alexa_request = AlexaRequest(request.get_json())
	alexa_response = AlexaResponse(alexa_request)

	status = kettle.current_status()

	logging.info(" REQUEST: Alexa Request: %s" % alexa_request.intent)

	if alexa_request.intent == "StartKettle":
		if status['is_boiling']:
			alexa_response.say("Kettle is already going")
		else:
			alexa_response.say("Okay")
			kettle.clickboil()

	elif alexa_request.intent == "SetTemperature":
		try:
			temp = int(alexa_request.slots['Temperature'])
		except ValueError:
			alexa_response.say("Sorry, I didn't understand that temperature")
			return jsonify(alexa_response.respond())


		if temp not in (65,85,95,100):
			alexa_response.say("Invalid temperature")
			return jsonify(alexa_response.respond())

		if not status['is_boiling']:
			kettle.clickboil()
			time.sleep(2)

		if status['temperature'] == temp:
			alexa_response.say("Already there")
		else:
			kettle.set_temp(temp)
			alexa_response.say("Heating to %d degrees" % temp)

	elif alexa_request.intent == "StopKettle":
		if status['is_boiling']:
			kettle.stopboil()
		else:
			alexa_response.say("Already off")

	elif alexa_request.intent == "KeepWarm":
		if status['is_warming']:
			alexa_response.say("Already on")
		else:
			kettle.togglewarm()

	elif alexa_request.intent == "KeepWarmStop":
		if status['is_warming']:
			kettle.togglewarm()
		else:
			alexa_response.say("Already on")

	elif alexa_request.intent == "GetStatus":
		statrep = "Kettle is %s boiling %s %s"
		if status['is_boiling']:
			boil = ""
			temp = "to %d degrees" % status['temperature']
		else:
			boil = "not "
			temp = "";

		if status['is_warming']:
			warm = "and will be kept there."
		else:
			warm = "";

		alexa_response.say(statrep % (boil, temp, warm))

	else:
		alexa_response.say("What?")


	return jsonify(alexa_response.respond())

