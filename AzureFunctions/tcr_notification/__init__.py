"""  
    Description:
        Web-Hook to collect Call Id's and write them to a Service Bus
    
    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
        
    Known issues:
"""

import logging
import urllib.parse
import json
import os
import sys
import azure.functions as func
from __app__.sb_eh_helper.sb_eh_helper import sbHelper
import __app__.constants.constants as constants

# Check query results and write to Service Bus
def main(req: func.HttpRequest) -> func.HttpResponse:
    
    logging.info('Python HTTP trigger function processed a request.')
    
    result = str()
    
    validationToken = req.params.get('validationToken')
    
    if not validationToken:
        try:
            req_body = json.dumps(req.get_json())
        except ValueError:
            req_body = None

        logging.info('Send Call-ID to Azure Service Bus: %s', constants.SB_CONNECTION_STR)
        sb_sender = sbHelper(constants.SB_CONNECTION_STR, constants.TOPIC_NAME, constants.SUBSCRIPTION_NAME)
        try:
            sb_sender.sb_send(req_body)
        except:
            sys.exit('Failed to send Call-ID to Azure Service Bus')

        return func.HttpResponse(
            result,
            status_code=200)
    else:
        return func.HttpResponse(
            urllib.parse.unquote_plus(validationToken),
            status_code=200)