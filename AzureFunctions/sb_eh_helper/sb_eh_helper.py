"""  
    Description:
        Module to interact with Service Bus and Event Hub

    Disclaimer:
        This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
        without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
        The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
        for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
        loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
        
    Known issues:

"""

import json
from azure.servicebus import ServiceBusClient, Message
from azure.eventhub import EventHubProducerClient, EventData
import logging

# Azure Service Bus Helper Class
class sbHelper:

    def __init__(self, connstr, topicName, subscriptionName):
        self.connstr = connstr
        self.topicName = topicName
        self.subscriptionName = subscriptionName

    def sb_client_sc(self):
        with ServiceBusClient.from_connection_string(self.connstr) as client:
            receiver = client.get_subscription_receiver(self.topicName, self.subscriptionName)

            return receiver

    def sb_send(self, str):
        with ServiceBusClient.from_connection_string(self.connstr) as client:
            with client.get_topic_sender(self.topicName) as sender:
                
                # Send message to Service Bus
                sender.send_messages(Message(str))
                
                #Close session
                sender.close()

    def sb_receive(self, receiver):
        # Receive messages from Service Bus
        received_msgs = receiver.receive_messages(max_message_count=19, max_wait_time=5)

        # Receive messages from Service Bus - ONLY USED IF BATCH QUERY > 20 MESSAGES IS USED
        #received_msgs = receiver.receive_messages(max_message_count=100, max_wait_time=10)

        # Return messages to process
        return received_msgs 

    def sb_cleanup(self, receiver, list):
        for msg in list:
            msg.complete()
        receiver.close()

    def sb_disconnect(self, receiver):
        receiver.close()

# Azure Event Hub Helper Class to write call records to Event Hub
class ehHelper:

    def __init__(self, calldetails):
        self.calldetails = calldetails
    
    def participantsTransform(self):
        participants = []
        for callDetail in self.calldetails:

            # Split call records in single participant objects incl. call-id
            for item in callDetail['participants']:
                participantsDict = {"id":callDetail["id"], "participants":[]}
                participantsDict["participants"].append(item)
                participants.append(participantsDict)

        return(participants)

    def sessionsTransform(self):
        sessions = []
        for callDetail in self.calldetails:

            # Split call records in single sessions objects incl. call-id
            for item in callDetail['sessions']:
                sessionsDict = {"id":callDetail["id"], "sessions":[]}
                sessionsDict["sessions"].append(item)
                sessions.append(sessionsDict)

        return(sessions)

    def callsTransform(self):
        calls_short = []
        for callDetail in self.calldetails:
            
            # Remove participants and sessions arrays from object
            callDetail.pop("participants", None)
            callDetail.pop("sessions", None)
            calls_short.append(callDetail)

        return(calls_short)
    
    def eh_send(self, eh_connstr, eh_name, callobjects):
        with EventHubProducerClient.from_connection_string(conn_str=eh_connstr, eventhub_name=eh_name) as producer:
            
            # Create batch for Event Hub
            cr_batch = producer.create_batch()
            
            # To catch batch exception
            batch_error = False

            # Add call records details to Event Hub batch
            for callobj in callobjects:

                try:
                    # Add call to Event Hub batch
                    cr_batch.add(EventData(json.dumps(callobj)))

                except ValueError as v_err: # EventDataBatch object reaches max_size
                    
                    logging.info(str(v_err))
                    
                    # Send batch to Event Hub
                    producer.send_batch(cr_batch)
                    # Create new batch
                    cr_batch = producer.create_batch()
                    # Add call to Event Hub batch
                    cr_batch.add(EventData(json.dumps(callobj)))

                except Exception as batch_error: # Unable to add calls to batch
                    batch_error = True
                    logging.error(str(batch_error))

            # Check if exception
            if not batch_error:

                # Check if calls list is empty
                if callobjects:

                    # Send batch to Event Hub
                    try: 
                        producer.send_batch(cr_batch)
                    
                    except Exception as send_err:
                        logging.error(str(send_err))
                    
                        # Close Event Hub Session
                        producer.close()
            else:
                producer.close()