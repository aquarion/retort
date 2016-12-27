

class AlexaRequest():

	request = False
	intent = False
	slots = False

	def __init__(self, request_data):
		self.request = request_data

		if "reason" in request_data['request'] and request_data['request']['reason'] == "ERROR":
			print request_data['request']['error']['message']

		if not "intent" in request_data['request']:
			print request_data
			return None

		self.intent = request_data['request']['intent']['name']


		if "slots" in request_data['request']['intent']:
			self.slots = {}
			for key in request_data['request']['intent']['slots']:
				slot = request_data['request']['intent']['slots'][key]
				print slot
				if "value" in slot:
					self.slots[slot['name']] = slot['value']
				else:
					self.slots[slot['name']] = True


	def sessionObject(self):
		return self.request['session']


class AlexaResponse():
	
	request = False
	version = 1.0

	returnSpeech = False
	returnSpeechSSML = False

	def __init__(self, request):
		self.request = request

	def respond(self):
		return {
			'version' : '1.0',
			'session' : self.request.sessionObject(),
			'response' : self.buildResponse(),
		}

	def speechObject(self):
		if self.returnSpeech:
			return {
				'type' : "PlainText",
				'text' : self.returnSpeech
			}
		elif self.returnSpeechSSML:
			return {
				'type' : "SSML",
				'ssml' : self.returnSpeechSSML
			}

		return False

	def cardObject(self):
		return False

	def repromptObject(self):
		return False

	def directivesObject(self):
		return False


	def buildResponse(self):
		response = {}

		speech = self.speechObject()
		if speech: 
			response['outputSpeech'] = speech

		card = self.cardObject()
		if card: 
			response['card'] = card

		reprompt = self.repromptObject()
		if reprompt: 
			response['reprompt'] = reprompt

		directives = self.directivesObject()
		if directives: 
			response['directives'] = directives

		response['shouldEndSession'] = True

		return response



	########################## Action responses

	def say(self, something):
		self.returnSpeech = something