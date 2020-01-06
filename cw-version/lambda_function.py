#import modules
import boto3
import json
import os
from datetime import datetime
from urllib.request import Request, urlopen, URLError, HTTPError
from urllib.parse import urlencode
from base64 import b64decode

#main function
def lambda_handler(event, context):
    
    #get webhook from environment variables
    encryptedWebHook = os.environ['encryptedWebHook']
    #open kms connection
    kms = boto3.client('kms')
    #decrypt webhook
    response = kms.decrypt(CiphertextBlob=b64decode(encryptedWebHook))['Plaintext']
    string_response = response.decode('ascii')
    decodedWebHook = "https://" + string_response
    #load sns message from sns json
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    #format time
    time = "%Y-%m-%d %H:%M:%S"
    print ("Message received: ", json.dumps(message))
    #create slack message to send
    slack_title = str("*:rotating_light:AWS CloudWatch Health Alert:rotating_light:*")
    slack_account = message['account']
    slack_region = message['region']
    slack_time = datetime.now().strftime(time)

    # check if sns message contains health API calls, affected entitys or resources
    if json.dumps(message['detail-type'])=='"AWS API Call via CloudTrail"':
            slack_message = {
                    "text": slack_title,
                    "attachments": [
                        {
                            "color": "danger",
                            "fields": [
                                { "title": "Account", "value": slack_account, "short": True },
                                { "title": "Region", "value": slack_region, "short": True },
                                { "title": "Posted Time (UTC)", "value": slack_time, "short": True },
                                { "title": "Service", "value": message['detail']['eventType'], "short": True },
                                { "title": "Description", "value": message['detail']['eventName'], "short": False },
                                { "title": "Username", "value": message['detail']['userIdentity']['userName'], "short": False }
                                ]
                        }
        ]
    }
    elif len(message['resources'])==0:
        slack_message = {
                        "text": slack_title,
                        "attachments": [
                            {
                                "color": "danger",
                                "fields": [
                                    { "title": "Account", "value": slack_account, "short": True },
                                    { "title": "Region", "value": slack_region, "short": True },
                                    { "title": "Posted Time (UTC)", "value": slack_time, "short": True },
                                    { "title": "Service", "value": message['detail']['service'], "short": True },
                                    { "title": "Description", "value": message['detail']['eventDescription'][0]['latestDescription'], "short": False },
                                    { "title": "Event Code", "value": message['detail']['eventTypeCode'], "short": False },
                                    { "title": "Resources", "value": message['detail']['affectedEntities'][0]['entityValue'].replace(',', '\n'), "short": False },
                                    { "title": "Start Time UTC", "value": message['detail']['startTime'], "short": False }
                                    ]
                            }
            ]
        }
    else:
        slack_message = {
                        "text": slack_title,
                        "attachments": [
                            {
                                "color": "danger",
                                "fields": [
                                    { "title": "Account", "value": slack_account, "short": True },
                                    { "title": "Region", "value": slack_region, "short": True },
                                    { "title": "Posted Time (UTC)", "value": slack_time, "short": True },
                                    { "title": "Service", "value": message['detail']['service'], "short": True },
                                    { "title": "Description", "value": message['detail']['eventDescription'][0]['latestDescription'], "short": False },
                                    { "title": "Event Code", "value": message['detail']['eventTypeCode'], "short": False },
                                    { "title": "Resources", "value": "\n".join(message['resources']), "short": False },
                                    { "title": "Start Time UTC", "value": message['detail']['startTime'], "short": False }
                                    ]
                            }
            ]
        }
    
    #send slack message to slack
    req = Request(decodedWebHook, data=json.dumps(slack_message).encode("utf-8"), headers={"content-type": "application/json"})
    try:
      response = urlopen(req)
      response.read()
      print("Message sent to slack: ", json.dumps(slack_message))
    except HTTPError as e:
       print("Request failed : ", e.code, e.reason)
    except URLError as e:
       print("Server connection failed: ", e.reason)