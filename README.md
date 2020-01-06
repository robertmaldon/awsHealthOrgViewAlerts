
![](https://github.com/jordanaroth/awsHealthToSlack/blob/master/assets/ah2s_logo.png?raw=true)


**Table of Contents**

- [Introduction](#introduction)
  * [Options](#options)
- [Instructions](#instructions)
  * [Create Incoming Slack Webhook](#create-incoming-slack-webhook)
  * [CloudWatch version](#cloudwatch-version)
      - [Architecture](#architecture)
    + [Overview](#overview)
      - [Single account deployment](#single-account-deployment)
      - [CloudFormation Stackset deployment](#cloudformation-stackset-deployment)
      - [CloudWatch Event Bus deployment](#cloudwatch-event-bus-deployment)
  * [Organization Health API version](#organization-health-api-version)
    + [Architecture](#architecture-1)
  * [Overview](#overview-1)
    + [Organization Master account deployment](#organization-master-account-deployment)
- [Troubleshooting](#troubleshooting)

# Introduction
AWS Health to Slack (AH2S) is an automated notification tool for sending well-formatted AWS Health events to your Slack channel.

There are two separate architectures depending on whether or not you have AWS Business/Enterprise support (which has access to the AWS Health API) and/or whether you are utilizing AWS Organizations which now has an AWS Organization Health API.

Below is a decision tree to help you know which version is best for you:

![](https://github.com/jordanaroth/awsHealthToSlack/blob/master/assets/decision_tree.png?raw=true)

## Options
* [Create Incoming Slack Webhook](#create-incoming-slack-webhook) then [CloudWatch version](#cloudwatch-version)
Or
* [Create Incoming Slack Webhook](#create-incoming-slack-webhook) then [Organization Health API version](#organization-health-api-version)

# Instructions
## Create Incoming Slack Webhook
Before you start you will need to create a Slack Webhook URL that the Lambda will be posting to. Within the architecture this webhook will be encrypted automatically. **You will need to have access to add a new channel and app to your Slack Workspace**.

1. Create a new [channel](https://slack.com/help/articles/201402297-Create-a-channel) for events (i.e. aws_events)
2. In your browser go to: workspace-name.slack.com/apps where workspace-name is the name of your Slack Workspace.
3. In the search bar, search for: *Incoming Webhooks* and **click** on it.
4. **Click** on *Add to Slack*
5. From the dropdown **click** on the channel your created in step 1 and **click** *Add Incoming Webhooks integration*
6. From this page you can change the name of the webhook (i.e. AWS Bot), the icon/emoji to use, etc.
7. For the deployment we will need the *Webhook URL*.

## CloudWatch version
Since either you do not have AWS Business/Enterprise support on all your accounts and/or you are not using AWS Organizations, we will be using aws.health CloudWatch events to notify SNS which will then trigger a Lambda to post to your Slack Webhook. There are 3 deployment methods for the CloudWatch version:

1. [**Single account deployment**](#single-account-deployment): One deployment that monitors the account it was deployed in.
2. [**CloudFormation Stackset deployment**](#cloudformation-stackset-deployment): Using CloudFormation Stacksets you deploy once to multiple accounts.
3. [**CloudWatch Event Bus deployment**](#cloudwatch-event-bus-deployment): Have multiple accounts send aws.health events to an account with a CloudWatch Event Bus and deploy in that account.

#### Architecture
![](https://github.com/jordanaroth/awsHealthToSlack/blob/master/assets/cw-version.png?raw=true)

| Resource | Description                    |
| ------------- | ------------------------------ |
| `SlackKMSKey`      | Key used to encrypt the Webhook URL       |
| `SlackKMSAlias`   | Friendly name for the SlackKMSKey for easy identification     |
| `LambdaKMSEncryptHook`      | Inline Lambda function used to take the WebhookURL and encrypt it against the SlackKMSKey       |
| `LambdaSNStoSlack`   | Main Lambda function that decrypts the WebhookURL and posts to Slack     |
| `EncryptLambdaExecutionRole`      | IAM role used for LambdaKMSEncryptHook       |
| `DecryptLambdaExecutionRole`   | IAM role used for LambdaSNStoSlack     |
| `KMSCustomResource`      | Provides the output of the LambdaKMSEncryptHook since KMS encrypt is not a built-in CloudFormation resource       |
| `SNStoSlackTopic`   | SNS Topic that receives the CloudWatch event and sends to LambdaSNStoSlack     |
| `CloudWatchHealthEventRule`      | Watches for any aws.health event and sends to SNStoSlackTopic       |
| `EventTopicPolicy`   | Allows events to get published to SNStoSlackTopic     |
| `SNSInvokeLambdaPermission`   | Allows SNS to invoke LambdaSNStoSlack     |

### Overview
#### Single account deployment
1. In the folder `cw-version` you will find two files you will need: `CFT_cw-version.yml` and `sns-slack.zip`.
2. Upload `sns-slack.zip` to S3 in the same region you plan to deploy this in.
3. In your AWS console go to *CloudFormation*.
4. In the *CloudFormation* console **click** *Create stack > With new resources (standard)*.
5. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_cw-version.yml` **Click** *Next*.
6. -In *Stack name* type a stack name (i.e. AWSHealth2Slack)
-In *Bucket* type ***just*** the name of the S3 bucket that contains `sns-slack.zip` (i.e. my-bucket-name)
-In *Key* type ***just*** the location of the `sns-slack.zip` (i.e. if in root bucket, sns-slack.zip or in a folder, foldername/sns-slack.zip)
-In *SlackURL* put in the *Webhook URL* you got from *Step 7* in the [Webhook Instructions](#create-incoming-slack-webhook) ***(without https:// in front)***. **Click** *Next*.
7. Scroll to the bottom and **click** *Next*.
8. Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.
9. Wait until *Status* changes to *CREATE_COMPLETE* (roughly 5-10 minutes)
10. You can test functionality by opening `sns_example.json` and going to '*Amazon SNS* in your console, going to *Topics* , **click** the *SNStoSlackTopic* and **click** *Publish message*. Paste in the text from the `sns_example.json` and **click** *Publish message*.

#### CloudFormation Stackset deployment
1. First you will need to deploy the `AWSCloudFormationStackSetAdministrationRole` in the account that will own the deployment (*parent account*) and the `AWSCloudFormationStackSetExecutionRole` in each account you will be deploying to (*child accounts*). Directions for that are located [here](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs.html).
2. Once you have deployed the roles correctly, in the folder `cw-version` you will find two files you will need: `CFT_cw-version.yml` and `sns-slack.zip`.
3. Upload `sns-slack.zip` to S3 in the same region you plan to deploy this in.
4. **Click** on the `sns-slack.zip` link in your S3 console and **click** *permissions*. From here you need to **click** on *Add account* and add every *child account* you plan to deploy this to with the *Read object* set to *Yes*. This allows the *child accounts* to read `sns-slack.zip` when deploying.
5. In your AWS console go to *CloudFormation*.
6. In the *CloudFormation* console **click** *StackSets* then *Create stackset*.
7. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_cw-version.yml` **Click** *Next*.
8. -In *Stack name* type a stack name (i.e. AWSHealth2Slack)
-In *Bucket* type ***just*** the name of the S3 bucket that contains `sns-slack.zip` (i.e. my-bucket-name)
-In *SlackURL* put in the *Webhook URL* you got from *Step 7* in the [Webhook Instructions](#create-incoming-slack-webhook) ***(without https:// in front)***
-In *Key* type ***just*** the location of the `sns-slack.zip` (i.e. if in root bucket, sns-slack.zip or in a folder, foldername/sns-slack.zip). **Click** *Next*.
9. Verify that the *IAM execution role name* is *AWSCloudFormationStackSetExecutionRole*. Scroll to the bottom and **click** *Next*.
10. In *Account numbers* enter in a comma-separated list of account numbers you want to deploy to (i.e. 123456789012,987654321987) OR select *Deploy stacks in organizational units* and enter in the OU identifier of the AWS Organizational Unit you want to deploy to (i.e. ou-123a-bc345de). **Click** the region you want to deploy the resouces to (you'll still get notified of aws.health issues in other regions, this is just for the stack resources). Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.
11. Wait until *Operations - Status* changes to *SUCCEEDED* (timing depends on number of accounts)
12. You can test functionality by opening `sns_example.json` and going to '*Amazon SNS* in the console of any account you deployed it to, going to *Topics* , **click** the *SNStoSlackTopic* and **click** *Publish message*. Paste in the text from the `sns_example.json` and **click** *Publish message*.

#### CloudWatch Event Bus deployment
1. We are going to enable sending and receiving events between accounts, process is outlined [here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/CloudWatchEvents-CrossAccountEventDelivery.html). In the account you are going to deploy the CloudFormation template to (*parent account*), go to the *CloudWatch*  console. **Click** *Event Buses* from the left and **click** *Add permission*. Add in the other accounts you want to monitor (*child accounts*) OR select your AWS Organization.
2. The next step can be very tedious with multiple *child accounts*, you can either do it one by one or write your own CloudFormation template to create the *Event Rules* in each *child account*. 
3. In each *child account* go to the *CloudWatch* console and **click** on *Rules*. **Click** *Create rule*. Under *Service Name* select *Health*, leave *Event Type* as *All Events*. On the right **click** *Add target*. **Click** on the dropdown and select *Event bud in another AWS account*. Enter in the *Account ID* of your *parent account*. Leave *Create a new rule for this specific resource* selected and **click** *Configure details*. Type in a *Name* for the rule (i.e. SlackNotificationEventBus) and **click** *Create rule*.
4. In the folder `cw-version` you will find two files you will need: `CFT_cw-version.yml` and `sns-slack.zip`.
5. Upload `sns-slack.zip` to S3 in the same region you plan to deploy this in.
6. In your AWS console go to *CloudFormation*.
7. In the *CloudFormation* console **click** *Create stack > With new resources (standard)*.
8. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_cw-version.yml` **Click** *Next*.
9. -In *Stack name* type a stack name (i.e. AWSHealth2Slack)
-In *Bucket* type ***just*** the name of the S3 bucket that contains `sns-slack.zip` (i.e. my-bucket-name)
-In *Key* type ***just*** the location of the `sns-slack.zip` (i.e. if in root bucket, sns-slack.zip or in a folder, foldername/sns-slack.zip)
-In *SlackURL* put in the *Webhook URL* you got from *Step 7* in the [Webhook Instructions](#create-incoming-slack-webhook) ***(without https:// in front)***. **Click** *Next*.
10. Scroll to the bottom and **click** *Next*.
11. Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.
12. Wait until *Status* changes to *CREATE_COMPLETE* (roughly 5-10 minutes)
13. You can test functionality by opening `sns_example.json` and going to '*Amazon SNS* in your console, going to *Topics* , **click** the *SNStoSlackTopic* and **click** *Publish message*. Paste in the text from the `sns_example.json` and **click** *Publish message*.

## Organization Health API version
When you have AWS Business/Enterprise Support on all your accounts AND are using AWS Organizations, you have access to [AWS Organization Health API](https://docs.aws.amazon.com/health/latest/APIReference/Welcome.html). So instead of waiting for an event to push, you can query the API and get Service Health and Personal Health Dashboard Events of all accounts in your Organization.

There is 1 deployment method for the Organization Health API version:

1. [**Organization Master account deployment**](#Organization%20Master%20account%20deployment): One deployment that monitors all accounts in an AWS organization where all accounts have AWS Business/Enterprise Support.

### Architecture
![](https://github.com/jordanaroth/awsHealthToSlack/blob/master/assets/org-version.png?raw=true)

| Resource | Description                    |
| ------------- | ------------------------------ |
| `SlackKMSKey`      | Key used to encrypt the Webhook URL       |
| `SlackKMSAlias`   | Friendly name for the SlackKMSKey for easy identification     |
| `SHDIssuesTable`   | DynamoDB Table used to store Event ARNs and updates     |
| `LambdaKMSEncryptHook`      | Inline Lambda function used to take the WebhookURL and encrypt it against the SlackKMSKey       |
| `LambdaAWSHealthStatus`   | Main Lambda function that decrypts the WebhookURL, reads and writes to SHDIssuesTable and posts to Slack     |
| `EncryptLambdaExecutionRole`      | IAM role used for LambdaKMSEncryptHook       |
| `DecryptLambdaExecutionRole`   | IAM role used for LambdaAWSHealthStatus     |
| `KMSCustomResource`      | Provides the output of the LambdaKMSEncryptHook since KMS encrypt is not a built-in CloudFormation resource       |
| `UpdatedBoto3`   | A Lambda Layer that includes the version of Boto3 that supports Organizational Health API (v. 1.10.45 or above)     |
| `SHDScheduledRule`      | Checks API every minute for an update       |
| `PermissionForEventstoInvokeLambda`   | Allows SHDScheduledRule to invoke LambdaAWSHealthStatus     |

## Overview
### Organization Master account deployment
**Disclaimer**: As of 2020-01-06, configuring and reading the AWS Organization Health API is **only** done via API calls. In other words, you can NOT see entries and/or status in the console. Also, ***AWS Organization Health Events only start working once you enable it (Step 1 below), which means any events that occurred before enabling, will not get added. You will need to wait for a Health event to happen to one of the accounts in your AWS Organization to verify everything is working correctly***.
1. The first thing you will need to do is enable [AWS Organization Health Service Access](https://docs.aws.amazon.com/health/latest/APIReference/API_EnableHealthServiceAccessForOrganization.html).  To do so, you need to run have python and the following packages installed: `awscli` and `boto3 (at least 1.10.45)`. Configure `awscli` for your AWS Organization Master account, instructions are [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html). Once configured, run the command `aws health enable-health-service-access-for-organization`, to verify it worked run `aws health describe-health-service-status-for-organization`. You should get a response back that says `"healthServiceAccessStatusForOrganization": "ENABLED"`. **Remember, only Health events that occurred from this point forward will be sent to Slack**.
2. In the folder `org-version` you will find three files you will need: `CFT_org-version.yml`, `healthapi-slack.zip` and `updated-boto3.zip`
3. Upload `healthapi-slack.zip` and `updated-boto3.zip` to S3 in the same region you plan to deploy this in.
4. In your AWS console go to *CloudFormation*.
4. In the *CloudFormation* console **click** *Create stack > With new resources (standard)*.
5. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_healthapi-version.yml` **Click** *Next*.
6. -In *Stack name* type a stack name (i.e. AWSHealth2Slack)
-In *Lambda Bucket* type ***just*** the name of the S3 bucket that contains `healthapi-slack.zip` (i.e. my-bucket-name)
-In *Lambda Key* type ***just*** the location of the `healthapi-slack.zip` (i.e. if in root bucket, sns-slack.zip or in a folder, foldername/sns-slack.zip)
-In *Layer Bucket* type ***just*** the name of the S3 bucket that contains `updated-boto3.zip`
-In *Layer Key* type ***just*** the location of the `updated-boto3.zip`
-In *EnvTimeToLiveSeconds* you can leave it default which will search back 4 hours each time (or change it to something bigger/smaller)
-In *Regions* leave it blank to search all regions or enter in a comma separated list of specific regions you want to alert on (i.e. us-east-1,us-east-2)
-In *SlackURL* put in the *Webhook URL* you got from *Step 7* in the [Webhook Instructions](##create-incoming-slack-webhook) ***(without https:// in front)***. **Click** *Next*.
7. Scroll to the bottom and **click** *Next*.
8. Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.
9. Wait until *Status* changes to *CREATE_COMPLETE* (roughly 5-10 minutes)
10. Unless you received an event on one of your AWS Organization accounts ***after*** you enabled the service in step 1, you will not get any notifications until an event occurs.

# Troubleshooting
* If for whatever reason you need to updat the Slack Webhook URL. Just update the CloudFormation Template with the new Webhook URL (minus the https:// of course) and the KMSEncryptionLambda will encrypt the new Webhook URL and update the DecryptionLambda.
* If you are expecting an event and it did not show up it may be an oddly formed event Take a look at CloudWatch > Log groups and look at the Lambda that sends to Slack.  See what the error is and reach out to me via [email](mailto:jordroth@amazon.com) for help.