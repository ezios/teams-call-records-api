"""  
    Description:
        Azure Function to subscribe to the Service Bus and query Call Records Details from Graph API and write it to Even Hub

    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
        
    Known issues:

"""

import logging
import requests
import sys
import azure.functions as func
from __app__.response_handler.response_handler import ResponseTransformer, batchCaller
from __app__.sb_eh_helper.sb_eh_helper import sbHelper, ehHelper
import __app__.constants.constants as constants


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Validate if required ingest string is provide in the JSON body
    try:
        req_body = req.get_json()
        tcrString = req_body.get('tcr_IngestString')
    except ValueError:
        tcrString = None

    # Execute run if correct ingest string was provided
    if tcrString == constants.INGEST_STRING:

        # Graph API/AAD URL's
        micallIDDetailURL = "/communications/callRecords/{0}?$expand=sessions($expand=segments)"
        authURL = "https://login.microsoftonline.com/{0}/oauth2/v2.0/token".format(constants.TENANT_ID)
        batchUrl = "https://graph.microsoft.com/v1.0/$batch"
        
        # build auth header to retreive AAD bearer token
        authbody = {
            "client_id" : constants.CLIENT_ID,
            "client_secret" : constants.CLIENT_SECRET,
            "grant_type" : "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }

        # get AAD bearer token
        response = requests.post(authURL, data= authbody)
        try:
            token = response.json()["access_token"]
        except:
            sys.exit('Failed to authentication token (wrong user/password)')

        # build header with Bearer token for HTTPS auth to MS GraphAPI
        batchHeaders= {
            "Authorization" : "Bearer {0}".format(token),
            "Content-Type":"application/json",
            "Accept":"application/json"                                
        }

        # Fetch ids from Service Bus
        sb_connect = sbHelper(constants.SB_CONNECTION_STR, constants.TOPIC_NAME, constants.SUBSCRIPTION_NAME)
        logging.info('Connect to Azure Service Bus: %s', constants.SB_CONNECTION_STR)
        sb_receiver = sb_connect.sb_client_sc()
        logging.info('Get Call-IDs from Azure Service Bus Topic: %s', constants.TOPIC_NAME)
        messages = sb_connect.sb_receive(sb_receiver)

        # Validate if Azure Service Bus responses included messages to process
        if len(messages) != 0:

            # Transform callIDs into a batch request
            logging.info('Filter and transform Azure Service Bus Query Response')
            crTransformer = ResponseTransformer(micallIDDetailURL)
            batchRequest = crTransformer.processChain(messages)

            # Post batch request to retreive CallDetails
            logging.info('Query Call-ID Batches against Teams Call Records Graph API')
            api_call = batchCaller(batchUrl, batchHeaders, batchRequest)
            batchResponse = api_call.graph_query()

            #Try to parse batch response
            try:
                callDetails = batchResponse.json()["responses"]
            except:
                callDetails = None
            
            # If the response body contains CallIDs
            if callDetails: 
                
                if any(batch_entry["status"] != 200 for batch_entry in callDetails):
                    sys.exit('Graph batch query response includes failed responses - HTTP status != 200')

                else:
                    callDetailsParsed = list(map(crTransformer.processCallDetails,callDetails))

                    # Ingest call records data to event hub
                    eh_ingest = ehHelper(callDetailsParsed)

                    # Send call-IDs and participants information to participants Event Hub
                    try:
                        logging.info('Send Participants to Azure Event Hub: %s', constants.EH_PARTICIPANTS_NAME)
                        participants = eh_ingest.participantsTransform()
                        eh_ingest.eh_send(constants.EH_PARTICIPANTS_CONNECTION_STR ,constants.EH_PARTICIPANTS_NAME , participants)
                    except:
                        sys.exit('Failed to send Participants to Azure Event Hub and/or close Session')

                    # Send call-IDs and sessions information to participants Event Hub
                    try:
                        logging.info('Send Sessions to Azure Event Hub: %s', constants.EH_SESSIONS_NAME)
                        sessions = eh_ingest.sessionsTransform()
                        eh_ingest.eh_send(constants.EH_SESSIONS_CONNECTION_STR, constants.EH_SESSIONS_NAME, sessions)
                    except:
                        sys.exit('Failed to send Sessions to Azure Event Hub and/or close Session')

                    # Send call-IDs and general call information to calls Event Hub
                    try:
                        logging.info('Send Calls to Azure Event Hub: %s', constants.EH_CALLS_NAME)
                        calls = eh_ingest.callsTransform()
                        eh_ingest.eh_send(constants.EH_CALLS_CONNECTION_STR, constants.EH_CALLS_NAME, calls)
                    except:
                        sys.exit('Failed to send Calls to Azure Event Hub and/or close Session')

                    # Remove processed messages from Service Bus and close session
                    logging.info('Remove processed messages from Azure Service Bus and close session')
                    sb_connect.sb_cleanup(sb_receiver, messages)
                    return func.HttpResponse("", status_code=200)

            else:
                # Close Service Bus session
                logging.info('No Call-IDs in the Topic at the moment. Closing Service Bus Connection: %s', constants.TOPIC_NAME)
                sb_connect.sb_disconnect(sb_receiver)
                return func.HttpResponse("", status_code=200)

        else:
            # Close Service Bus session
            logging.info('Empty response came back from Azure Service Bus. Closing Service Bus Connection: %s', constants.TOPIC_NAME)
            sb_connect.sb_disconnect(sb_receiver)
            return func.HttpResponse("", status_code=200)

    else:
        logging.error('This HTTP triggered function execution failed. Pass the ingest string in the request body.')
        return func.HttpResponse(
            "This HTTP triggered function execution failed. Pass the ingest string in the request body.",
            status_code=504
            )
