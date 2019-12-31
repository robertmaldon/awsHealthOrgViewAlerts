#import packages
import boto3
import json
import decimal
import configparser
import logging
import os
from urllib.request import Request, urlopen, URLError, HTTPError
from urllib.parse import urlencode
from datetime import datetime
from dateutil import parser
from base64 import b64decode
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

#date differential function
def diff_dates(strDate1, strDate2):
    intSecs = float(strDate2)-float(strDate1)
    return intSecs

#dynamoDB function
def update_ddb(objTable, strArn, strUpdate, now, intSeconds):
    response = objTable.put_item(
      Item ={
        'arn' : strArn,
        'lastUpdatedTime' : strUpdate,
        'added' : now,
        'ttl' : int(now) + int(intSeconds) + 3600
      }
    )
    
#aws.health message for slack    
def get_healthUpdates(awshealth, event, strArn, awsRegion):
    event_details = awshealth.describe_event_details (
      eventArns=[
        strArn,
      ]
    )
    json_event_details = json.dumps(event_details, cls=DatetimeEncoder)
    parsed_event_details = json.loads (json_event_details)
    healthUpdates = (parsed_event_details['successfulSet'][0]['eventDescription']['latestDescription'])#print parsed_event_deta
    return healthUpdates    

#create health subject function 
def get_healthSubject(event):
    eventTypeCode = str(event['eventTypeCode'])
    service = str(event['service'])
    region =  str(event['region'])
    eventName = eventTypeCode + ' - ' + service + ' - ' + region
    return eventName

#send to slack function
def send_webhook(updatedOn, eventName, event, strArn, awsRegion, decodedWebHook, healthUpdates):
    slack_title = str("*:rotating_light:AWS Health Dashboard Alert:rotating_light:*")
    slack_message = {
                    "text": slack_title,
                    "attachments": [
                        {
                            "color": "danger",
                            "fields": [
                                { "title": "Service", "value": str(event['service']), "short": True },
                                { "title": "Region", "value": str(event['region']), "short": True },
                                { "title": "Posted Time (UTC)", "value": updatedOn, "short": True },
                                { "title": "Status", "value": str(event['statusCode']), "short": True },
                                { "title": "Updates", "value": str(healthUpdates), "short": False }
                                ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "Link to Health Dashboard Event",
                            "url": "https://phd.aws.amazon.com/phd/home?region=" + awsRegion + "#/event-log?eventID=" + strArn + "&eventTab=details&layout=vertical"
                        }
                        ]         
                        }
        ]
    }
    req = Request(decodedWebHook, data=json.dumps(slack_message).encode("utf-8"), headers={"content-type": "application/json"})
    try:
      response = urlopen(req)
      response.read()
      print("Message sent to slack: ", json.dumps(slack_message))
    except HTTPError as e:
       print("Request failed : ", e.code, e.reason)
    except URLError as e:
       print("Server connection failed: ", e.reason)


#time encoder class
class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(DatetimeEncoder, obj).default(obj)
        except TypeError:
            return str(obj)

#main function
def lambda_handler(event, context):
    intSeconds = os.environ['ttl']  #14400
    dictRegions = os.environ['regions']
    encryptedWebHook = os.environ['encryptedWebHook']
    ddbTable = os.environ['ddbTable']
    awsRegion = os.environ['AWS_DEFAULT_REGION']
    
    if dictRegions != "":
        dictRegions = dictRegions.replace("'","")
        dictRegions = list(dictRegions.split(",")) 
        print (dictRegions)
    
    #set standard date time format used throughout
    strDTMFormat2 = "%Y-%m-%d %H:%M:%S"
    strDTMFormat = '%s'
        
    # creates health object as client.  AWS health only has a us-east-1 endpoint currently
    awshealth = boto3.client('health', region_name='us-east-1')
    dynamodb = boto3.resource("dynamodb")
    kms = boto3.client('kms')
    
    response = kms.decrypt(CiphertextBlob=b64decode(encryptedWebHook))['Plaintext']
    string_response = response.decode('ascii')
    decodedWebHook = "https://" + string_response

    SHDIssuesTable = dynamodb.Table(ddbTable)

    strFilter = {'eventTypeCategories': ['investigation', 'accountNotification', 'issue', 'scheduledChange']}

    if dictRegions != "":
    	strFilter = {
	    		dictRegions
    	}

    response = awshealth.describe_events (
        filter=
            strFilter
        ,
    )

    json_pre = json.dumps(response, cls=DatetimeEncoder)
    json_events = json.loads (json_pre)

    events = json_events.get('events')
    for event in events :
        strEventTypeCode = event['eventTypeCode']
        strArn = (event['arn'])
        strUpdate = parser.parse((event['lastUpdatedTime']))
        strUpdate = strUpdate.strftime(strDTMFormat)
        now = datetime.strftime(datetime.now(),strDTMFormat)
        if diff_dates(strUpdate, now) < int(intSeconds):
            try:
                response = SHDIssuesTable.get_item(
                    Key = {
                        'arn' : strArn
                    }
            )
            except ClientError as e:
                print(e.response['Error']['Message'])
            else:
                isItemResponse = response.get('Item')
                if isItemResponse == None:
                    print (datetime.now().strftime(strDTMFormat2)+": record not found")
                    update_ddb(SHDIssuesTable, strArn, strUpdate, now, intSeconds)
                    healthUpdates = get_healthUpdates(awshealth, event, strArn, awsRegion)
                    eventName = get_healthSubject(event)
                    print ("eventName: ", eventName)
                    send_webhook(datetime.now().strftime(strDTMFormat2), eventName, event, strArn, awsRegion, decodedWebHook, healthUpdates)
                else:
                    item = response['Item']
                    if item['lastUpdatedTime'] != strUpdate:
                      print (datetime.now().strftime(strDTMFormat2)+": last Update is different")
                      update_ddb(SHDIssuesTable, strArn, strUpdate, now, intSeconds)
                      healthUpdates = get_healthUpdates(awshealth, event, strArn, awsRegion)
                      eventName = get_healthSubject(event)
                      print ("eventName: ", eventName)
                      send_webhook(datetime.now().strftime(strDTMFormat2), eventName, event, strArn, awsRegion, decodedWebHook, healthUpdates)