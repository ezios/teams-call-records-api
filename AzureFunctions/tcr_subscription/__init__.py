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
import json
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
        "client_secret" : constants.CLIENT_SECRET,
        "grant_type" : "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }

    # Fetch Authentication Token form Graph API
    authresponse = requests.post('https://login.microsoftonline.com/{0}/oauth2/v2.0/token'.format(constants.TENANT_ID), data= authbody)
    
    if authresponse.status_code != 200:
        raise Exception('Query for Auth-Token failed - Check Authentication Body')

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

    # Get current active subscriptions
    subRes = requests.get(subscriptionUrl, headers= headers)

    if subRes.status_code == 200:

        # Parse the response to JSON
        sub_Json = json.loads(subRes.text)

        # Check if paging is required
        if '@odata.nextLink' in sub_Json.keys():
        
            logging.info("Result includes paging - Iterate through additional result pages")

            # Get Link to next page
            subNextLink = sub_Json['@odata.nextLink']
            
            # Repeat until no paging link is provided
            while subNextLink != None:
                # Query next page
                pagingQuery = requests.get(subNextLink, headers= headers)
                
                if pagingQuery.status_code == 200:
                    paging_JSON = json.loads(pagingQuery.text)

                    # Add subscription to total result    
                    activeSubs = len(paging_JSON['value'])
                    i = 0
                    while i < activeSubs:
                        sub_Json['value'].append(paging_JSON['value'][i])
                        i += 1
                    
                    # Check if additional an paging link is provided
                    if '@odata.nextLink' in paging_JSON.keys():
                        subNextLink = paging_JSON['@odata.nextLink']
                    else:
                        subNextLink = None

                else:
                    raise Exception("Failed to query nextLink of paged subscription response")

    else:
        raise Exception("Failed to query existing Graph API subscriptions")

    # Check subscription query response if Call Records API subscription is included
    ids = my_subscriptionCheck(sub_Json)

    # Experation time for subscription (new or patch)
    expiryTime = (datetime.utcnow() + timedelta(minutes=4229)).isoformat() + "Z"

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
        
        # POST new subscription
        createResponse = requests.post(subscriptionUrl, headers= headers, json= newSubBody)

        if createResponse.status_code != 201:
            raise Exception('Failed to create new subscription - Please check subscription body')

        logging.info(createResponse.text)

    # Check if more then one subscription exists
    elif len(ids) > 1:
        raise Exception('More then one Call Records API subscriptions found. Please check the subscription count manually and resolve the problem')

    else: 
        # Get the subscription-Id as string
        id = str(ids[0])
        
        # Create PATCH subscription body
        expirationBody = {
            "expirationDateTime" : expiryTime
        }

        # PATCH existing subscription
        logging.info("One Call Records API subscriptions found - Patch existing subscription")
        
        patchRes = requests.patch('{0}/{1}'.format(subscriptionUrl,id), headers= headers, json= expirationBody)

        if patchRes.status_code != 200:
            raise Exception('Failed to patch existing Subscription')

        logging.info(patchRes.text)