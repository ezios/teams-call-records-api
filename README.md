# teams-call-records-api

| [About The Project](#about-the-project) | [Usage](#usage) | [Prerequisites](#prerequisites) | [Deployment](#deployment) | [Cost Estimate](#cost-estimate) | [Appendix](#appendix)
| ---- | ---- | ---- | ---- | ---- | ---- |

Sample project to collect the Microsoft Teams Call Records data. 

The offical Microsoft documentation about the Call Records API can be found here:  
[Working with the call records API in Microsoft Graph](https://docs.microsoft.com/en-us/graph/api/resources/callrecords-api-overview?view=graph-rest-1.0)


> :warning: **This is not an offical solution by Microsoft**. This **example** should demonstrate an potential process on how to collect Microsoft Teams call records data using Graph API and Azure ressources.

## Table of Contents

- [project-scrubs](#project-scrubs)
  - [Table of Contents](#table-of-contents)
  - [About The Project](#about-the-project)
    - [Built With](#built-with)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Deployment](#deployment)
      - [1. Clone the repo or download the files directly](#1-Clone-the-repo-or-download-the-files-directly)
      - [2. Update the Configuration file](#2-update-the-configuration-file)
      - [3. Run the deployment script](#3-run-the-deployment-script)
      - [4. Publish the Azure Function with VSCode](#4-publish-the-azure-function-with-vscode)
      - [5. Update the Azure Function Configuration](#5-update-the-azure-function-configuration)
      - [6. Create the required tables in the ADX](#6-create-the-required-tables-in-the-adx)
      - [7. Create the data connections in ADX](#7-create-the-data-connections-in-adx)
      - [8. Create the subscription](#8-create-the-subscription)
      - [9. Test Call](#9-test-call)
      - [10. Scale-Out Options](#10-scale-out-options)
  - [Usage](#usage)
  - [Roadmap](#roadmap)
  - [Cost Estimate](#cost-estimate)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)
  - [Appendix](#appendix)


## About The Project

This project provides an example how to store the Microsoft Teams calls records data to Azure Kusto.

The solution is build with Python-based Azure Functions an Service Bus and Event Hubs to store the Microsoft Teams call data to ADX (Azure Data Explorer) also known as Kusto.

The following diagram shows how the data get stored:  
![Solution Overview](https://www.tnext-labs.com/GitHub/teams-call-records-api/teams-call-records-api_overview.png?raw=true)  

1. Azure Function to build and renew the Graph API Subscription
1. Azure Function as Webhook to receive new call-id's after a call ends
1. Call-id's are written to a Azure Service Bus
1. Time Triggered Azure Function('s) to trigger an additional function (Ingest) to proccess the call-id's
1. Ingest Azure Function to fetch new call-id's from the Service Bus
1. The function will then query the call records data from Graph API in a batch (20 call-id's)
1. Then the call data will be split into 3 segments (Call, Participants, Sessions) and send to 3 Event Hubs. Data Connection's in ADX will write these segments then to corresponding tables in a database inside the cluster.

The data can then be directly queried based on the call-id's using KQL or Power BI for example. All data is stored in row JSON format as dynamic fields and require some additional data transformation based on your needs. In Addition, also other sources like ASN information or network details can be added to seperate tables to allow even more enhanced queries.


### Built With

* Python
* PowerShell
* [Graph API](https://docs.microsoft.com/en-us/graph/api/resources/callrecords-api-overview?view=graph-rest-1.0)
* [Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/)
* [Azure Service Bus](https://docs.microsoft.com/en-us/azure/service-bus-messaging/service-bus-messaging-overview)
* [Azure Event Hub](https://docs.microsoft.com/en-us/azure/event-hubs/)
* [Azure Data Explorer](https://docs.microsoft.com/en-us/azure/data-explorer/)

## Getting Started

To get a copy up and running make sure to meet the requirements and follow the steps below.

> :exclamation: Please make sure to first explore how the solution is build and then pilot the solution in an lab or demo enviroment before you consider any production use.

### Prerequisites

The solution require an Office 365 and Azure subscription including the following:

- Demo environment (Office 365 and Azure Subscription)
- [Azure Command-Line Interface (CLI)](https://docs.microsoft.com/en-us/cli/azure/)
- [Azure Az PowerShell Module](https://docs.microsoft.com/en-us/powershell/azure/new-azureps-module-az?view=azps-6.3.0)
- [Visual Studio Code](https://code.visualstudio.com/)
- Access to Azure AD to create an App Registration
- Access to an Azure subscription to create a new Ressource Group and the required components in it

### Deployment

#### 1. Clone the repo or download the files directly

Clone the repo:

```sh
git clone https://github.com/tobiheim/teams-call-records-api.git
```

#### 2. Update the Configuration file

First you need to adjust the configuration file **deploy-config.json**. This file will include all the details for the PowerShell-based deployment.

Here an example:

```json
{
    "tenant": {
        "subscriptionId": "a4d1fd10-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "tenantId": "f7bed8uc-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    },
    "azureGeneral": {
        "Location": "<Azure Location e.g westeurope>",
        "appRegistrationName": "<App Registration Name>",
        "resourceGroup": "<Resource Group Name>"
    },
    "serviceBus": {
        "service_BusNamespace_Name": "<Service Bus Namespace>",
        "serviceBusName": "<Service Bus Topic Name>",
        "serviceBusSubscriptionName": "<Service Bus Subscription Name>",
        "serviceBusAuthenticationRule": "<Service Bus Authentication Rule Name>"
    },
    "eventHubs": {
        "eventHubNamespaceName": "<Event Hub Namespace>"
    },
    "kustoCluster": {
        "kustoClusterName": "<Azure Data Explorer Clustername>"
    },
    "functionApp": {
        "functionAppName": "<Function App Name>"
    }
}
```

In the [Appendix](#appendix) you can find additional details on how to get the tenant- and subscription-id. 

Make sure that all selected names are using an allowed syntax for the indivitual Azure components.

You can find more details here:  
[Considerations for naming Azure resources](https://docs.microsoft.com/en-us/azure/azure-government/documentation-government-concept-naming-resources#:~:text=Naming%20considerations%20Customers%20should%20not%20include%20sensitive%20or,Examples%20of%20sensitive%20information%20include%20data%20subject%20to%3A)


#### 3. Run the deployment script

Make sure that the two [required PowerShell Modules](#prerequisites) are already installed.

Next you can run the Azure deployment. The script requires the following nessacary parameters:  

`./deploy.ps1 -AdminUsername <Azure Subscription and Global Admin> -Mfa <$true or $false>`  


|Parameter  |Description  |
|---------|---------|
|AdminUserName     |Admin Account that has access to Azure AD to create an App Registration and is also able to access an Azure subscription to create the required components.         |
|Mfa     |If your Account requires an additional form of authentication you can set Mfa to True. Expect additional pop-ups to appear.         |

**Do not change the folder structure** of the **Deployment** folder because the script rely on it.

After a successful run of the script you should get the following output:  

![PS Success](https://www.tnext-labs.com/GitHub/teams-call-records-api/PS_Deploy_success.png?raw=true)


#### 4. Publish the Azure Function with VSCode

Next you need to publish the functions to the newly created Azure function app. Open VsCode and then open the folder **Azure Functions** from the cloned repository. 

Make sure that the Azure Function extentsion is already installed in your VsCode. Either install the **Azure Tools** or the **Azure Functions** extension.  

![PS Success](https://www.tnext-labs.com/GitHub/teams-call-records-api/Vscode_Extension.png?raw=true)

Before you can publish the functions you need get the name of the deployed function app from the Azure portal.  

![Function app name](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-name.png?raw=true)

When you now open the Azure extension from your left panel in VsCode you should see the functions under **Local Project**. Use the **Deploy to Function App...** option as shown below to publish the functions to Azure.

> Note: If the **Local Project** remain empty then you need to create new local project first.

![Deploy functions](https://www.tnext-labs.com/GitHub/teams-call-records-api/deploy-functions.png?raw=true)

You should now see a list of all your available function apps. Select the one that the script created for you earlier.

![Deploy functions](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-selection.png?raw=true)

Click **Deploy** to start the deployment.

You should see the following after functions are succesfully deployed.

![Deployment completed](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-deploy-complete.png?raw=true)

Leave VsCode open. You will need it later again.


#### 5. Update the Azure Function Configuration

Now you need to update pre-created values inside the function app configuration based on the deployed functions in the previous step.

Go to the Azure function app in the Azure Portal and navigate to the **Functions** section.  

![View functions](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-overview.png?raw=true)

Open the highlighted **HTTP Trigger** functions to **Get the Function Url**.  

![Get URL](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-urls.png?raw=true)

Store the URL because you need it in the upcoming steps. Repeat the same step also for the other HTTP Trigger function.

Now you can add the Urls to the function app configuration as shown below.

![Adjust values in function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-config.png?raw=true)

Please adjust the URL placeholder as shown in the following table:

|Function Name  |Function Configuration Value Name  |
|---------|---------|
|tcr_notification URL     |API_NOTIFICATION_URL         |
|tcr_ingest_webhook URL   |INGESTFUNC_URL         |

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/function-app-updated-values.png?raw=true)


#### 6. Create the required tables in the ADX

As next step you need to create the required tables inside your Azure Data Explorer cluster. To do so, you can either use the Kusto Application, the VsCode extension or the Kusto Web Explorer. In this example we will use the Web Explorer.

Before you can do this, you need to copy the URI of your Cluster.

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-cluster-name.png?raw=true)

Open the [Kusto Web Explorer](https://web.kusto.windows.net/) and sign-in. Now you can add your cluster.

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-add-cluster.png?raw=true)

Now create the required tables in your cluster. Use the example below:

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-create-table.png?raw=true)


```kusto
.create table calls (callid:string, call:dynamic)

.create table participants (callid:string, participant:dynamic)

.create table sessions (callid:string, session:dynamic)
```

> Keep the breaks in between each line and run them one by one. The selected one will be highlighted in light-blue. This applies also to the following steps.

Next enable the ingest timestamp using the following examples:

```kusto
.alter table calls policy ingestiontime true

.alter table participants policy ingestiontime true

.alter table sessions policy ingestiontime true
```

As last step in Kusto you need to build the ingest mapping:

```kusto
.create-or-alter table calls ingestion json mapping "calls"
'['
'    { "column" : "callid", "Properties":{"Path":"$.id"}},'
'    { "column" : "call", "Properties":{"Path":"$"}}'
']'


.create-or-alter table participants ingestion json mapping "participants"
'['
'    { "column" : "callid", "Properties":{"Path":"$.id"}},'
'    { "column" : "participant", "Properties":{"Path":"$.participants"}}'
']'

.create-or-alter table sessions ingestion json mapping "sessions"
'['
'    { "column" : "callid", "Properties":{"Path":"$.id"}},'
'    { "column" : "session", "Properties":{"Path":"$.sessions"}}'
']'
```

#### 7. Create the data connections in ADX

Now you can create the data connections for the Kusto cluster based on your three Event Hubs.

Select the created **database**:

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-db-select.png?raw=true)

Select **Data Connections**:

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-select-data-connections.png?raw=true)

Add an new data connection:

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-select-new-connection.png?raw=true)

Configure the data connection as shown below:

![Adjusted function app config](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto-connection-creation.png?raw=true)

Repeat the steps in this section for the two additonal required data connections:

- participants
- sessions

#### 8. Update the subscription

Before you able to update the renew time of the subscription, you need to verify that the subscription was created successfully.
There a two available options:

- Use the Azure Function Monitor
- Run the following Powershell Example

The PowerShell example require the app registration information that are stored inside the Azure function configuration.


```powershell
#region App Registration values
$ClientID = "<App Registration Client Id"
$ClientSecret = "<App Registration Client Secret>"
$TenantId = "<Tenant Id>"

#endregion
#region Get Access Token

$Body = @{
    client_id=$ClientID
    client_secret=$ClientSecret
    grant_type="client_credentials"
    scope="https://graph.microsoft.com/.default"
}
$OAuthReq = Invoke-RestMethod -Method Post -Uri https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token -Body $Body
$AccessToken = $OAuthReq.access_token

#endregion 
#region Create Webhook Subscription

## Request Header
$Headers= @{'Authorization' = "Bearer $AccessToken"
            'Content-Type'='application/json'
            'Accept'='application/json'                                
}

## Webhook Subscription URL
$SubscriptionUrl = "https://graph.microsoft.com/v1.0/subscriptions"

## Post Webhook Subscription Request
$get = Invoke-RestMethod -Uri $SubscriptionUrl -Headers $Headers -Method GET

if (!$get.value) {
    Write-Host('No subscription found for the tenant id:' -f $TenantId)
} else {
    $get.value
}

#endregion
```
The expected output should look like this:


```powershell
id                        : XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
resource                  : communications/callRecords
applicationId             : XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
changeType                : created
clientState               :
notificationUrl           : https://psfuncapp29-ht3nw.azurewebsites.net/api/...
notificationQueryOptions  :
lifecycleNotificationUrl  :
expirationDateTime        : 2021-08-29T11:04:00.250604Z
creatorId                 : XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
includeResourceData       :
latestSupportedTlsVersion : v1_2
encryptionCertificate     :
encryptionCertificateId   :
notificationUrlAppId      :
```



As a final step you need to update the **tcr_subscription** function time trigger configuration in VsCode.
Change the **schedule** value to "0 0 */4176 * * *" in the **function.json** as shown below and re-deploy the functions as you did the the step [4. Publish the Azure Function with VSCode](#4-publish-the-azure-function-with-vscode).


```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */4176 * * *"
    }
  ]
}
```

![Configure Subscription](https://www.tnext-labs.com/GitHub/teams-call-records-api/configure-subscription.png?raw=true)

Additonal details about the NCRONTAB expressions can be found here:
[Timer trigger for Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=csharp)

#### 9. Test Call

:telephone_receiver: Run a couple of test calls and check if the data get stored in the Kusto cluster. Keep in mind that it will take up to **15min.** until the Graph API will send the call id to the configured webhook.
Furthermore, also consider the additonal time (default: 5min.) configured in the Time Trigger function **tcr_ingest_trigger** when the function should run. *(More details can be found in the next section)*

:mag_right: You can verfiy this be using the following query:
![Kusto Check Count](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto_check_count.png?raw=true)


#### 10. Scale-out options

The default configuration of this solution will trigger the data ingest (for 20 calls at a time) every 5 Min. You can simple lower the **schedule** time inside the **tcr_ingest_trigger** function in the **function.json** file as shown below:

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */5 * * * *"
    }
  ]
}
```

If you have to handle a large amount of calls in your tenant then you can create additional function apps and **only** deploy the following function and helper modules in there. This will allow you to trigger the **tcr_ingest_webhook** function in parallel based on the **schedule** value definded in the function.json. Make sure to update the function app configuration accordingly in the newly created function apps.

Example additional function app:
```
constants
    constants.py
tcr_ingest_trigger
    __ini__.py
    function.json
.funcignore
host.json
proxies.json
requirements.txt
```

## Usage

This sample project should shad some light on a potential process on how the Microsoft Teams call records data can be collected. Kusto will allow you to query large datasets very effectively in almost no time.

You can easially add additional tables and datasets to combine them in your queries to achive great results.

Example Query:
![Simple Sample Query](https://www.tnext-labs.com/GitHub/teams-call-records-api/kusto_query_example.png?raw=true)

For the visualisation Power BI could be leveraged, to provide great looking visuals.

> :bar_chart: This project currently don't included details on how to transform and query the stored data. You can find more details here:  
>[Getting started with Kusto](https://docs.microsoft.com/en-us/azure/data-explorer/kusto/concepts/)  
>[Visualize data using the Azure Data Explorer connector for Power BI](https://docs.microsoft.com/en-us/azure/data-explorer/power-bi-connector)

## Cost Estimate

The solutions uses **sample SKUs/ Tier's** in all the provided sample Azure ARM Templates. Please make sure to adjust them accordingly based on your requirements and cost estimation.  

Example:  
![ARM SKU sample](https://www.tnext-labs.com/GitHub/teams-call-records-api/SKU-sample.png?raw=true)  

You can find more details about the pricing of the used components here:  
[Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/?OCID=AID2200190_SEM_2992fef4dc3b15fab4f89fd06df69890:G:s&ef_id=2992fef4dc3b15fab4f89fd06df69890:G:s&msclkid=2992fef4dc3b15fab4f89fd06df69890&dclid=CJ32q9OiyfICFRT_dwodHLkPRQ)


## Roadmap  

- Include paging support for truncated responses.

See the [open issues](https://github.com/tobiheim/teams-call-records-api/issues) for a list of proposed features (and known issues).

## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Appendix

### Get Azure Location

To select an Azure location for your resources you can run the following cmdlet using the Azure Az PowerShell Module:

`(Get-AzLocation).location`

### Get Tenant Id and Subscription Id

To get the tenant and Subscription Id, you can run the following cmdlet using the Azure Az PowerShell Module:

`Get-AzSubscription |Select-Object -Property Id, Tenantid |ft`

### Azure Python SDKs

If you need more details about the used SDKs please visit the links below:  
[Azure Event Hubs client library for Python](https://azuresdkdocs.blob.core.windows.net/$web/python/azure-eventhub/5.0.0b4/index.html)  
[Azure Service Bus client library for Python](https://azuresdkdocs.blob.core.windows.net/$web/python/azure-servicebus/7.0.0b7/index.html)