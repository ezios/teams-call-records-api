"""  
    Description:
        Create and renew the Teams Call Records API subscription

    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
        
    Known issues:
"""

import requests
import uuid
import sys, json
from datetime import datetime, timedelta, timezone
import logging
import azure.functions as func
import __app__.constants.constants as constants

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(
        tzinfo=timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    # Function to check subscription query response
    def my_subscriptionCheck (queryResponse):
        
        subscriptionIds = []

        for query in queryResponse['value']:
            if query['resource'] == "communications/callRecords":
                subscriptionIds.append(query['id'])

        return subscriptionIds

    # Auth body to request the token
    authbody = {
        "client_id" : constants.CLIENT_ID,
        "client_secret" : constants.CLIENT_SECRECT,
        "grant_type" : "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }

    # Fetch Authentication Token form Graph API
    try:
        authresponse = requests.post('https://login.microsoftonline.com/{0}/oauth2/v2.0/token'.format(constants.TENANT_ID), data= authbody)
    except:
        sys.exit('Query for Auth-Token failed - Check Authentication Body')

    if authresponse == None:
        sys.exit('Failed to get access token Auth-Token')
    else:
        accessToken = authresponse.json()['access_token']

    # Graph API Subscription Header
    headers = {
        "Authorization" : "Bearer {0}".format(accessToken),
        "Content-Type" : "application/json",
        "Accept" : "application/json"      
    }

    ## Webhook Subscription URL
    subscriptionUrl = "https://graph.microsoft.com/v1.0/subscriptions"

    ## New expiry time for subscription renewal
    expiryTime = (datetime.utcnow() + timedelta(minutes=4229)).isoformat() + "Z"

    # Get current active subscriptions
    subResponse = json.loads(requests.get(subscriptionUrl, headers= headers).text)

    # Check subscription query response
    ids = my_subscriptionCheck(subResponse)

    # Create new subscription
    if len(ids) == 0:
        logging.info("No Call Records API subscriptions found - Create new subscription")
        
        # Create random GUID
        guid = str(uuid.uuid4())

        # New subscription body
        newSubBody = {
            "changeType" : "created",
            "clientState" : guid,
            "expirationDateTime" : expiryTime,
            "notificationUrl" : constants.NOTIFICATION_URL,
            "resource" : "communications/callRecords"
        }
        
        try:
            # POST new subscription to Graph API
            createResponse = requests.post(subscriptionUrl, headers= headers, json= newSubBody)
            logging.info(createResponse.text)
        except:
            sys.exit('Failed to create new subscription - Please check subscription body')

    elif len(ids) > 1:
        sys.exit('More then one Call Records API subscriptions found')

    else: 
        # Get the Call Id as string
        id = str(ids[0])
        
        # Create PATCH subscription body
        expirationBody = {
            "expirationDateTime" : expiryTime
        }

        # PATCH existing subscription
        logging.info("One Call Records API subscriptions found - Patch existing subscription")
        
        try:
            patchResponse = requests.patch('{0}/{1}'.format(subscriptionUrl,id), headers= headers, json= expirationBody)
            logging.info(patchResponse.text)
        except:
            sys.exit('More then one Call Records API subscriptions found')
            