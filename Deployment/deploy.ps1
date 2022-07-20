## Teams-Call-Records-API Deployment Script
<#
.SYNOPSIS
    Deploys required assets of the "Teams-Call-Records-API" solution.
.DESCRIPTION
    Deploys a Service Bus, Event Hubs, ADX and an Azure Function App for the Teams Call Records API solution.
.PARAMETER AdminUsername
    UserPrincipalName (UPN) of the Azure / Office 365 Admin Account.
.PARAMETER Mfa
    Defines is Multi-Factor Authentication is required.
.EXAMPLE
    ./deploy.ps1 -AdminUsername <Azure Subscription and Global Admin> -Mfa <$true or $false>

-----------------------------------------------------------------------------------------------------------------------------------
Authors : Tobias Heim
Version : 1.0.1
-----------------------------------------------------------------------------------------------------------------------------------

DISCLAIMER:
    This code is provided AS IS without warranty of any kind. The author disclaim all implied warranties including, 
    without limitation, any implied warranties of merchantability or of fitness for a particular purpose. 
    The entire risk arising out of the use or performance remains with you. In no event will be the author liable 
    for any damages, whatsoever (including, without limitation, damages for loss of business profits, business interruption, 
    loss of business information, or other pecuniary loss) arising out of the use of or inability to use the code. 
#>

<# Valid Azure locations
DisplayName          Latitude    Longitude    Name
-------------------  ----------  -----------  ------------------
East Asia            22.267      114.188      eastasia
Southeast Asia       1.283       103.833      southeastasia
Central US           41.5908     -93.6208     centralus
East US              37.3719     -79.8164     eastus
East US 2            36.6681     -78.3889     eastus2
West US              37.783      -122.417     westus
North Central US     41.8819     -87.6278     northcentralus
South Central US     29.4167     -98.5        southcentralus
North Europe         53.3478     -6.2597      northeurope
West Europe          52.3667     4.9          westeurope
Japan West           34.6939     135.5022     japanwest
Japan East           35.68       139.77       japaneast
Brazil South         -23.55      -46.633      brazilsouth
Australia East       -33.86      151.2094     australiaeast
Australia Southeast  -37.8136    144.9631     australiasoutheast
South India          12.9822     80.1636      southindia
Central India        18.5822     73.9197      centralindia
West India           19.088      72.868       westindia
Canada Central       43.653      -79.383      canadacentral
Canada East          46.817      -71.217      canadaeast
UK South             50.941      -0.799       uksouth
UK West              53.427      -3.084       ukwest
West Central US      40.890      -110.234     westcentralus
West US 2            47.233      -119.852     westus2
Korea Central        37.5665     126.9780     koreacentral
Korea South          35.1796     129.0756     koreasouth
France Central       46.3772     2.3730       francecentral
France South         43.8345     2.1972       francesouth
Australia Central    -35.3075    149.1244     australiacentral
Australia Central 2  -35.3075    149.1244     australiacentral2
South Africa North   -25.731340  28.218370    southafricanorth
South Africa West    -34.075691  18.843266    southafricawest

#>

Param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true)][String]$AdminUsername,
    [Parameter(Mandatory = $true)][bool]$Mfa
)

Write-Host "Starting Microsoft Teams Call Records API Sample Solution Deployment`nVersion 1.0.1 - July 2022" -ForegroundColor Yellow

#region global functions

# Function to check if required config files exists
function checkIfFileExists ($FileOrFolder) {
    if (!(Test-Path $FileOrFolder)) {
        throw('Please make sure that the following file or folder exists: {0}' -f $FileOrFolder)
    }
}

# Function to check if the provided location is a valid Azure location
function validateAzureLocation {
    param (
        [String]$Location
    )
    $AzureLocations = (Get-AzLocation).Location
    if (!($AzureLocations | Where-Object {$_ -eq $Location})) {
        throw('Please provide a valid location (https://azure.microsoft.com/en-gb/global-infrastructure/locations/): {0}' -f $Location)
    }
}

# Function to create Azure resource group 
function createResourceGroup {
    param (
        [string]$AzureRgName,
        [string]$AzureLocation
    )
    if (Get-AzResourceGroup -Name $AzureRgName -ErrorAction:SilentlyContinue) {
        Write-Host('Azure resource group already exists: {0}' -f $AzureRgName)
    }
    else {
        try {
            Write-Host('Creating Azure resource group: {0}' -f $AzureRgName)
            New-AzResourceGroup -Name $AzureRgName -Location $AzureLocation -ErrorAction:Stop
            Write-Host('Successfully created resource group: {0}' -f $AzureRgName)
        }
        catch {
            throw('Failed to create Azure resource group {0}: {1}' -f $AzureRgName, $_.Exception.Message)
        }
    }
}

# Function to check Azure app regirstration
function getAzureADApp {
    param (
        [String]$Name
    )
    $app = az ad app list --filter "displayName eq '$Name'" |ConvertFrom-Json
    return $app
}

# Function to create or update the required Azure app registration
function createAzureADApp {
    param (
        [String]$appName,
        [string]$manifestPath
    )
    # Check if the app already exists
    $app = GetAzureADApp -Name $appName
    
    if ($app) {
        # Update Azure ad app registration using Azure CLI
        Write-Host('Azure AD App Registration {0} already exists - updating existing app...' -f $appName)
        az ad app update --id $app.appId --required-resource-accesses $manifestPath |Out-Null
        if (!$?) {
            throw('Failed to update AD App {0}' -f $appName)
        }
        Write-Host "Waiting for App Registration to finish updating..."
        Start-Sleep -s 60
        Write-Host('Updated Azure AD App Registration: {0}' -f $AppName)
    } 
    else {
        # Create Azure ad app registration using Azure CLI
        Write-Host('Creating Azure AD App Registration: {0}...' -f $appName)
        az ad app create --display-name $appName --required-resource-accesses $manifestPath |Out-Null
        if (!$?) {
            throw('Failed to create AD App Registration {0}' -f $appName)
        }
        Write-Host('Waiting for App Registration {0} to finish creating...' -f $appName)
        Start-Sleep -s 60
        Write-Host('Successfully created Azure AD App Registration: {0}...' -f $appName)

        # Get the app registration details
        $app = GetAzureADApp -Name $appName
    }

    # End-date for the secret is set to 90 days from now
    $endDate = (Get-Date).AddDays(90).ToString("yyyy-MM-dd")

    # Set the app registration secret
    Write-Host('Setting Azure AD App Registration Secret: {0}...' -f $appName)
    $appSec = az ad app credential reset --id $app.appId --end-date $endDate
    if (!$?) {
        throw('Failed to set Azure AD App Registration Secret: {0}' -f $appName)
    }
    # Get app registration secret
    $appDetails = $appSec |ConvertFrom-Json
    $appSecValue = ($appDetails).password

    # Grant admin consent for app registration required permissions using Azure CLI
    Write-Host('Granting admin content to App Registration: {0}' -f $appName)
    az ad app permission admin-consent --id $app.appId |Out-Null
    if (!$?) {
        throw('Failed to grant admin content to App Registration: {0}' -f $appName)
    }
    Write-Host "Waiting for admin consent to complete..."
    Start-Sleep -s 60
    Write-Host('Granted admin consent to App Regiration: {0}' -f $AppName)

    return $appSecValue
}

# Function to create Service Bus (incl. Subscription and Access Rules)
function createServiceBusTopic {
    param (
        [String]$ResourceGroup,
        [String]$SubscriptionId,
        [string]$ServiceBusArmTemplate,
        [string]$ServiceBusNamespace,
        [string]$ServiceBusTopic,
        [string]$ServiceBusSubscription,
        [string]$ServiceBusAuthenticationRule 
    )
    # Check if Service Bus already exists
    $serviceBus = az resource list --name $ServiceBusNamespace |ConvertFrom-Json
    if (!$serviceBus) {
        # Deploy Azure Service Bus
        Write-Host "Deploying Azure Service Bus..."
        az deployment group create --resource-group $ResourceGroup --subscription $SubscriptionId --template-file $ServiceBusArmTemplate --parameters "service_BusNamespace_Name=$ServiceBusNamespace" "serviceBusTopicName=$ServiceBusTopic" "serviceBusSubscriptionName=$ServiceBusSubscription" "serviceBusTopicAuthRule=$ServiceBusAuthenticationRule"
        if (!$?) {
            throw('Failed to create Azure Service Bus: {0}' -f $ServiceBusNamespace)
        }
    } else {
        Write-Host('Azure Service Bus Namespace {0} already exists - Skip Service Bus Deployment...' -f $ServiceBusNamespace)
    }
}

# Function to create Event Hub
function createEventHub {
    param (
        [String]$ResourceGroup,
        [String]$SubscriptionId,
        [string]$EventHubArmTemplate,
        [string]$EventHubNamespace
    )
    # Check if Event Hubs already exists
    $EventHub = az resource list --name $EventHubNamespace |ConvertFrom-Json
    if (!$EventHub) {
        # Deploy Event Hubs
        Write-Host "Deploying Azure Event Hubs..."
        az deployment group create --resource-group $ResourceGroup --subscription $SubscriptionId --template-file $EventHubArmTemplate --parameters "eventHubNamespaceName=$EventHubNamespace"
        if (!$?) {
            throw('Failed to create Azure Event Hubs: {0}' -f $EventHubNamespace)
        }
    } else {
        Write-Host('Azure Event Hubs Namespace {0} already exists - Skip Event Hubs Deployment...' -f $EventHubNamespace)
    }
}

# Function to create Kusto Cluster
function createKustoCluster {
    param (
        [String]$ResourceGroup,
        [String]$SubscriptionId,
        [string]$KustoArmTemplate,
        [string]$KustoClusterName
    )
    # Check if Kusto Cluster already exists
    $Adx = az resource list --name $KustoClusterName |ConvertFrom-Json
    if (!$Adx) {
        # Deploy Kusto Cluster and Database
        Write-Host ('Deploying Azure Kusto Cluster {0} ...' -f $KustoClusterName)
        az deployment group create --resource-group $ResourceGroup --subscription $SubscriptionId --template-file $KustoArmTemplate --parameters "clusters_kustocluster_name=$KustoClusterName"
        if (!$?) {
            throw('Failed to create Kusto Cluster Name: {0}' -f $KustoClusterName)
        }
    } else {
        Write-Host('Azure Kusto Cluster Name Namespace {0} already exists - Skip Kusto Cluster Name Deployment...' -f $KustoClusterName)
    }
}

# Function to create Azure Function App and publish Python code
function createFunctionApp {
    param (
        [String]$ResourceGroup,
        [String]$SubscriptionId,
        [String]$TenantId,
        [string]$FunctionAppArmTemplate,
        [string]$functionAppName,
        [string]$AppRegistrationName,
        [string]$AppRegistrationSecret,
        [string]$ServiceBusSubscription,
        [string]$ServiceBusTopic,
        [string]$serviceBusPrimaryConnection,
        [string]$ehCallPrimaryConnection,
        [string]$ehPartPrimaryConnection,
        [string]$ehSesPrimaryConnection
    )

    # Check if Azure Function App already exists
    $funcAppSearchString = ($functionAppName + "-")
    $funcApp = az resource list --query "[?contains(name, '$funcAppSearchString')]" |ConvertFrom-Json

    # Get App Registration ID
    $appId = (GetAzureADApp -Name $AppRegistrationName).appId

    # Azure Function additional Parameters
    $storageAccountName = "sa" + ($functionAppName).ToLower() + -join (((97..122) |ForEach-Object {[char]$_}) + (0..9) |Get-Random -Count 4)
    $appInsightsName = "ai" + ($functionAppName).ToLower() + -join (((97..122) |ForEach-Object {[char]$_}) + (0..9) |Get-Random -Count 4)
    $INGEST_STRING = (-join (((65..90) + (97..122) |ForEach-Object {[char]$_}) + (0..9) |Get-Random -Count 23))
    $functionAppName += ("-" + -join (((97..122) |ForEach-Object {[char]$_}) + (0..9) |Get-Random -Count 5))

    # Azure Function ARM Parameters JSON
    $functionParamsJson = @"
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "name": {
            "value": $('"' + $functionAppName + '"')
        },
        "storageAccountName": {
            "value": $('"' + $storageAccountName + '"')
        },
        "appInsightsName": {
            "value": $('"' + $appInsightsName + '"')
        },
        "APP_REGISTRATION_CLIENT_ID": {
            "value": $('"' + $appId + '"')
        },     
        "APP_REGISTRATION_CLIENT_SECRET":{
            "value": $('"' + $AppRegistrationSecret + '"')
        },
        "APP_REGISTRATION_TENANT_ID": {
            "value": $('"' + $TenantId + '"')
        },  
        "EVENT_HUB_CALLS_CONNECTION_STR":{
            "value": $('"' + $ehCallPrimaryConnection + '"')
        },
        "EVENT_HUB_PARTICIPANTS_CONNECTION_STR": {
            "value": $('"' + $ehPartPrimaryConnection + '"')
        },
        "EVENT_HUB_SESSIONS_CONNECTION_STR":{
              "value": $('"' + $ehSesPrimaryConnection + '"')
        },
        "INGEST_STRING": {
            "value": $('"' + $INGEST_STRING + '"')
        },
        "SERVICE_BUS_CONNECTION_STR": {
            "value": $('"' + $serviceBusPrimaryConnection + '"')
        },
        "SERVICE_BUS_SUBSCRIPTION_NAME": {
                "value": $('"' + $ServiceBusSubscription + '"')
        },
        "SERVICE_BUS_TOPIC_NAME": {
                "value": $('"' + $ServiceBusTopic + '"')
        }
    }
}
"@

    if (!$funcApp) {

        # Write temporary Azure Function Parameters file to Script Root Path
        $appFuncParamsJson = (Join-Path $PSScriptRoot -ChildPath ($functionAppName + "-" + (Get-Date -Format "MMddyy-HHMMss") + ".json"))
        $functionParamsJson |Out-File $appFuncParamsJson

        # Deploy Azure Function App
        Write-Host ('Deploying Azure Function App {0} ...' -f $functionAppName)
        az deployment group create --resource-group $ResourceGroup --subscription $SubscriptionId --template-file $FunctionAppArmTemplate --parameters @$appFuncParamsJson
        if (!$?) {
            throw('Failed to create Azure Function App: {0}' -f $functionAppName)
        }

        # Clean-Up (Delete Temp Parameters file)
        Write-Host ('Waiting some time for the Azure Function App to finish...')
        Start-Sleep 15
        Remove-Item $appFuncParamsJson

    } else {
        Write-Host('Azure Function App {0} already exists - Skip Azure Function Deployment...' -f $functionAppName)
    }
}

#endregion
#region Deployment Credentials

# Credential Object for Non-Mfa scenario
if (!$Mfa) {
    $Adminpwd = Read-Host "Please enter the Password of the O365 and Azure Administrator" -AsSecureString
    [PSCredential]$creds = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList($AdminUsername, $Adminpwd) 
}

#endregion
#region validation of configuration files and module installation incl. connect to Azure

# Configfiles required for the Deployment
$tcraConfigfile = Join-Path $PSScriptRoot -ChildPath "\deploy-config.json"
$SbArmTemplate = Join-Path $PSScriptRoot -ChildPath "\Config\servicebus-topic.json"
$ehArmTemplate = Join-Path $PSScriptRoot -ChildPath "\Config\eventhub.json"
$adxArmTemplate = Join-Path $PSScriptRoot -ChildPath "\Config\kusto-database.json"
$functionAppArmTemplate = Join-Path $PSScriptRoot -ChildPath "\Config\function-app.json"
$appManifest = Join-Path $PSScriptRoot -ChildPath "\Config\app-manifest.json"

# Check for presence of Azure CLI
If (!(Test-Path -Path "C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2")) {
    throw("AZURE CLI not installed!`nPlease visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest")
}

# Check for presence of Az PowerShell
If (!(Get-InstalledModule -Name "Az" -ErrorAction:SilentlyContinue)) {
    throw("Azure Powershell Module not installed!`nPlease run: Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force")  
}

# Check required Config files
Write-Host "Check if all required Configuration files exists..."
$reqConfFiles = $tcraConfigfile, $SbArmTemplate, $ehArmTemplate, $adxArmTemplate, $functionAppArmTemplate, $appManifest
foreach ($confFile in $reqConfFiles) {
    checkIfFileExists -FileOrFolder $confFile
}

# Script Variables imported from JSON config-file
$config = Get-Content $tcraConfigfile | ConvertFrom-Json
$SubscriptionId = $config.tenant.SubscriptionId
$TenantId = $config.tenant.tenantId
$Location = $config.azureGeneral.Location
$ResourceGroup = $config.azureGeneral.ResourceGroup
$AppRegistrationName = $config.azureGeneral.AppRegistrationName
$sbNamespace = $config.serviceBus.service_BusNamespace_Name
$sbTopic = $config.serviceBus.serviceBusName
$sbSubscription = $config.serviceBus.serviceBusSubscriptionName
$sbAuthRule = $config.serviceBus.serviceBusAuthenticationRule
$ehNamespace = $config.eventHubs.eventHubNamespaceName
$kustoClusterName = $config.kustoCluster.kustoClusterName
$functionAppName = $config.functionApp.functionAppName

# Connect to Azure
$Error.Clear()

if (!$Mfa) {
    Write-Host 'Connect to Azure Subscription...'
    Connect-AzAccount -Credential $creds -Tenant $TenantId -Subscription $SubscriptionId |Out-Null
    if ($error.count -gt 0) {
        throw('Failed to connect to Azure: {0}' -f $_.Exception.Message)
    }
    Write-Host 'Connect to Azure CLI...'
    try {
        az login -u $creds.UserName -p $creds.GetNetworkCredential().Password --tenant $TenantId |Out-Null
    } catch {
        throw('Failed to connect to Azure (AZ): {0}' -f $_.Exception.Message)
    }  
} else {
    Write-Host 'Connect to Azure Subscription...'
    Connect-AzAccount -Tenant $TenantId -Subscription $SubscriptionId |Out-Null
    if ($error.count -gt 0) {
        throw('Failed to connect to Azure: {0}' -f $_.Exception.Message)
    }
    Write-Host 'Connect to Azure CLI...'
    try {
        az login --tenant $TenantId |Out-Null
    } catch {
        throw('Failed to connect to Azure (AZ): {0}' -f $_.Exception.Message)
    }
}

# Validate provided Azure location
validateAzureLocation -Location $Location

#endregion
#region Azure Deployment

# Create Azure resource group
createResourceGroup -AzureRgName $ResourceGroup -AzureLocation $Location

# Create or Update Azure App Regiration and get the App Registration Secret
$appSecret = createAzureADApp -appName $AppRegistrationName -manifestPath $appManifest

# Create Azure Service Bus
$sbParams = @{
    ResourceGroup = $ResourceGroup 
    SubscriptionId = $SubscriptionId 
    ServiceBusArmTemplate = $SbArmTemplate
    ServiceBusNamespace = $sbNamespace 
    ServiceBusTopic = $sbTopic
    ServiceBusSubscription = $sbSubscription
    ServiceBusAuthenticationRule = $sbAuthRule
}
createServiceBusTopic @sbParams

# Create Azure Event Hubs
$ehParams = @{
    ResourceGroup = $ResourceGroup 
    SubscriptionId = $SubscriptionId 
    EventHubArmTemplate = $ehArmTemplate 
    EventHubNamespace = $ehNamespace
}
createEventHub @ehParams

# Create Azure Kusto Cluster and Database
$adxParams = @{
    ResourceGroup = $ResourceGroup 
    SubscriptionId = $SubscriptionId 
    KustoArmTemplate = $adxArmTemplate
    KustoClusterName = $kustoClusterName
}
createKustoCluster @adxParams

# Get Service Bus and Event Hub Primary Connection Strings
$serviceBusPrimaryConnection = (Get-AzServiceBusKey -ResourceGroupName $ResourceGroup -Namespace $sbNamespace -Topic $sbTopic -Name $sbAuthRule).PrimaryConnectionString
$ehCallPrimaryConnection = (Get-AzEventHubKey -ResourceGroupName $ResourceGroup -Namespace $ehNamespace -EventHub calls -Name sap_calls).PrimaryConnectionString
$ehPartPrimaryConnection = (Get-AzEventHubKey -ResourceGroupName $ResourceGroup -Namespace $ehNamespace -EventHub participants -Name sap_participants).PrimaryConnectionString
$ehSesPrimaryConnection = (Get-AzEventHubKey -ResourceGroupName $ResourceGroup -Namespace $ehNamespace -EventHub sessions -Name sap_sessions).PrimaryConnectionString

# Create Azure Function App
$faParams = @{
    ResourceGroup = $ResourceGroup
    SubscriptionId = $SubscriptionId
    TenantId = $TenantId
    FunctionAppArmTemplate = $FunctionAppArmTemplate
    FunctionAppName = $functionAppName
    AppRegistrationName = $AppRegistrationName
    AppRegistrationSecret = $appSecret
    ServiceBusSubscription = $sbSubscription
    ServiceBusTopic = $sbTopic
    serviceBusPrimaryConnection = $serviceBusPrimaryConnection
    ehCallPrimaryConnection = $ehCallPrimaryConnection
    ehPartPrimaryConnection = $ehPartPrimaryConnection
    ehSesPrimaryConnection = $ehSesPrimaryConnection
    
}
createFunctionApp @faParams

# Clear Passwords and Credentials from variables
$Adminpwd = $null
$creds = $null
$appSecret = $null

#endregion

Write-Host "Successfully deployed Microsoft Teams Call Records API Sample Solution. `nComplete the configuration based on the provided guidance on GitHub." -ForegroundColor Green