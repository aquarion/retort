import urllib2
import base64
import os

def lambda_handler(event, context):
    access_token = event['payload']['accessToken']

    if event['header']['namespace'] == 'Alexa.ConnectedHome.Discovery':
        return handleDiscovery(context, event)

    elif event['header']['namespace'] == 'Alexa.ConnectedHome.Control':
        return handleControl(context, event)

def handleDiscovery(context, event):
    print "Hello Discovery event"
    payload = ''
    header = {
        "namespace": "Alexa.ConnectedHome.Discovery",
        "name": "DiscoverAppliancesResponse",
        "payloadVersion": "2"
        }

    if event['header']['name'] == 'DiscoverAppliancesRequest':
        payload = {
            "discoveredAppliances":[
                {
                    "applianceId":"WifiKettle",
                    "manufacturerName":"Smarter",
                    "modelName":"1",
                    "version":"1.",
                    "friendlyName": "Smarter Wifi Kettle",
                    "friendlyDescription":"Connection of Smarter kettle via Retort interface",
                    "isReachable":True,
                    "actions":[
                        "turnOn",
                        "turnOff",
                        "setTargetTemperature"
                    ],
                    "additionalApplianceDetails":{
                        # "extraDetail1":"optionalDetailForSkillAdapterToReferenceThisDevice",
                        # "extraDetail2":"There can be multiple entries",
                        # "extraDetail3":"but they should only be used for reference purposes.",
                        # "extraDetail4":"This is not a suitable place to maintain current device state"
                    }
                }
            ]
        }
    return { 'header': header, 'payload': payload }

def handleControl(context, event):
    payload = ''
    device_id = event['payload']['appliance']['applianceId']
    message_id = event['header']['messageId']

    payload = {}

    print "Hello %s event" %  event['header']['name']
    if event['header']['name'] == 'TurnOnRequest':
        doTurnOn(context, event)
        response = "TurnOnConfirmation"
    elif event['header']['name'] == 'TurnOffRequest':
        doTurnOff(context, event)
        response = "TurnOffConfirmation"
    elif event['header']['name'] == 'SetTargetTemperatureRequest':
        print "Triggering SetTargetTemperatureRequest"
        (response, payload) = doSetTemp(context, event)


    header = {
        "namespace":"Alexa.ConnectedHome.Control",
        "name": response,
        "payloadVersion":"2",
        "messageId": message_id
        }
    return { 'header': header, 'payload': payload }

def sendRequest(path):
    url = "%s/%s" % (os.environ['url'], path)
    print " - URL: %s" % url
    request = urllib2.Request(url)
    base64string = base64.b64encode('%s:%s' % (os.environ['username'], os.environ['password']))
    request.add_header("Authorization", "Basic %s" % base64string)   
    response = urllib2.urlopen(request)

def doTurnOn(context, event):
    sendRequest("start")

def doTurnOff(context, event):
    sendRequest("stop")

def doSetTemp(context, event):

    temp = event['payload']['targetTemperature']['value']

    print "Set temperature to %s" % temp

    if temp > 100 or temp < 65:
        payload = {
            "minimumValue":65.0,
            "maximumValue":100.0
          }
        response = "ValueOutOfRangeError"
    elif temp not in (65,80,95,100):
        print "%s isn't in range" % temp
        response = "UnableToSetValueError"
        payload = {
            "errorInfo":{
                "code":"NOT_CALIBRATED",
                "description":"%s is an invalid temperature. Try 65, 80, 95 or 100" % temp
            }
        }
    else:
        print "Set temperature to %s" % temp
        sendRequest("temp/%d" % temp)
        
        response = "SetTargetTemperatureConfirmation"
        payload = { "targetTemperature":{
                     "value": temp
                 }
            }

    print response
    print payload
    return (response, payload)