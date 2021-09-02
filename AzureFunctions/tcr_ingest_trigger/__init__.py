"""  
    Description:
        Azure Function to trigger the Ingest Function

    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
        
    Known issues:
"""

import datetime
import logging
import requests
import sys
import azure.functions as func
import __app__.constants.constants as constants


def main(mytimer: func.TimerRequest) -> None:

    # Header - Body will contain required JSON key and value 
    headers = {
        "Content-Type" : "application/json",      
    }

    # JSON Body - TCR ingest string. The string need to be add the function configuration
    body = {
        "tcr_IngestString": constants.INGEST_STRING
    }
    
    # Post to Ingest Trigger Function
    logging.info('Post to Call Records Ingest Function')

    try:
        # Post will timeout after 5 sec and wont wait on response code
        requests.post(constants.INGESTFUNC_URL, headers=headers, json=body, timeout=5)
    except requests.Timeout:
        pass
    except requests.ConnectionError:
        pass

    logging.info('Post to Call Records Ingest Function successful')
