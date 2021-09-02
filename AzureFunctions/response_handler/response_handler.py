"""  
    Description:
        Helper Module to build batch queries for the Graph API

    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code.  
        
    Known issues:

"""

import json, time, requests

class ResponseTransformer:

    def __init__(self, tcr_callIDDetailURL):
        self.tcr_callIDDetailURL = tcr_callIDDetailURL

    def parseBody(self,message):
        tcr_str = str(message)
        try:
            callID = json.loads(tcr_str)["value"][0]["resourceData"]["id"]
        except:
            callID = None

        return callID

    def tcr_buildnestedRequest(self,arrayItem):
        tcr_headerlist = ["id", "url"]
        requestjson = dict(zip(tcr_headerlist, arrayItem))
        requestjson['method'] = "GET"

        return requestjson

    def buildBatchRequest(self,requestArray):
        batchRequest = '{"requests": ' + json.dumps(requestArray) + '}'

        return batchRequest

    def buildRequestURL(self,callID):

        # Build call records query URL
        requesturl = self.tcr_callIDDetailURL.format(callID)

        return requesturl

    def processCallDetails(self,callDetail):

        return callDetail["body"]

    def processChain(self, messages):
        
        #extract CallIDs
        tcr_parsed = list(map(self.parseBody, messages))
        
        #filter Nones from array in case the CallID could not have been extracted
        tcr_filtered = list(filter(None,tcr_parsed))
        
        #build requestURL
        tcr_requestURL = list(map(self.buildRequestURL,tcr_filtered))
        
        #create index position
        tcr_index = list(enumerate(tcr_requestURL, 1))
        
        #build entire request for single CallDetail
        tcr_requestList = list(map(self.tcr_buildnestedRequest,tcr_index))

        batchRequest = self.buildBatchRequest(tcr_requestList)

        return batchRequest

# NOTE: Class is only required if > 20 messages per run are proccessed in an batch operation
class BatchCreator:
    
    def __init__(self, list):
        self.list = list

    def divider(self): 
      
        n = 20
        for i in range(0, len(self.list), n):  
            yield self.list[i:i + n] 


class batchCaller:

    def __init__(self, batchUrl, batchHeaders, batchRequest):
        self.batchUrl = batchUrl
        self.batchHeaders = batchHeaders
        self.batchRequest = batchRequest

    def graph_query(self):
        
        max_retries = 3
        i = 1
        while max_retries >= i:
            response = requests.post(url= self.batchUrl, headers= self.batchHeaders, data= self.batchRequest)
            if response.status_code == 200:
                return response
            else:
                time.sleep(20*i)
                i += 1