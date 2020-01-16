
![](https://github.com/jordanaroth/awsHealthToSlack/raw/master/assets-images/ahova_banner.png?raw=true)


**Table of Contents**

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Deployment](#deployment)
  * [AHOVA for Amazon Chime](#ahova-for-amazon-chime)
    + [Create Incoming Amazon Chime Webhook](#create-incoming-amazon-chime-webhook)
    + [Install AHOVA for Amazon Chime](#install-ahova-for-amazon-chime)
  * [AHOVA for Slack](#ahova-for-slack)
    + [Create Incoming Slack Webhook](#create-incoming-slack-webhook)
    + [Install AHOVA for Slack](#install-ahova-for-slack)
- [Troubleshooting](#troubleshooting)

# Introduction
AWS Health Organizational View Alerts (AHOVA) is an automated notification tool for sending well-formatted AWS Health Organization Alerts to your Amazon Chime or Slack room/channel if are utilizing an AWS Organization and have Business or Enterprise Support on all accounts in the Organization.

# Architecture
![](https://github.com/jordanaroth/awsHealthToSlack/raw/master/asset-images/architecture.png?raw=1)

| Resource | Description                    |
| ------------- | ------------------------------ |
| `KMSKey`      | Key used to encrypt the Webhook URL       |
| `KMSAlias`   | Friendly name for the KMSKey for easy identification     |
| `SHDIssuesTable`   | DynamoDB Table used to store Event ARNs and updates     |
| `LambdaKMSEncryptHook`      | Inline Lambda function used to take the WebhookURL and encrypt it against the KMSKey       |
| `LambdaAWSHealthStatus`   | Main Lambda function that decrypts the WebhookURL, reads and writes to SHDIssuesTable and posts to channel/room     |
| `EncryptLambdaExecutionRole`      | IAM role used for LambdaKMSEncryptHook       |
| `DecryptLambdaExecutionRole`   | IAM role used for LambdaAWSHealthStatus     |
| `KMSCustomResource`      | Provides the output of the LambdaKMSEncryptHook since KMS encrypt is not a built-in CloudFormation resource       |
| `UpdatedBoto3`   | A Lambda Layer that includes the version of Boto3 that supports Organizational Health API (v. 1.10.45 or above)     |
| `SHDScheduledRule`      | Checks API every minute for an update       |
| `PermissionForEventstoInvokeLambda`   | Allows SHDScheduledRule to invoke LambdaAWSHealthStatus     |

# Deployment
When you have AWS Business/Enterprise Support on all your accounts AND are using AWS Organizations, you have access to [AWS Organization Health API](https://docs.aws.amazon.com/health/latest/APIReference/Welcome.html). So instead of waiting for an event to push, you can query the API and get Service Health and Personal Health Dashboard Events of all accounts in your Organization.

There 2 deployment methods for AHOVA:

1. [**AHOVA for Amazon Chime**](#ahova-for-amazon-chime): One deployment that monitors all accounts in an AWS organization where all accounts have AWS Business/Enterprise Support and posts to Amazon Chime.
2. [**AHOVA for Slack**](#ahova-for-slack): One deployment that monitors all accounts in an AWS organization where all accounts have AWS Business/Enterprise Support and posts to Slack.

## AHOVA for Amazon Chime  

### Create Incoming Amazon Chime Webhook
Before you start you will need to create a Amazon Chime Webhook URL that the Lambda will be posting to. Within the architecture this webhook will be encrypted automatically. **You will need to have access to create an Amazon Chime room and manage webhooks**.

1. Create a new [chat room](https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html) for events (i.e. aws_events).   
2. In the chat room created in step 1, **click** on the gear icon and **click** *manage webhooks and bots*.   
3. **Click** *Add webhook*.   
4. **Type** a name for the bot (i.e. AHOVA Bot) and **click** *Create*.   
5. **Click** *Copy URL*, we will need it for the deployment.

### Install AHOVA for Amazon Chime
**Disclaimer**: As of 2020-01-15, configuring and reading the AWS Health Organizational View API is **only** done via API calls. In other words, you can NOT see entries and/or status in the console. Also, ***AWS Health Organizational View Alerts only starts working once you enable it (Step 1 below), which means any events that occurred before enabling, will not get added. You will need to wait for a Health event to happen to one of the accounts in your AWS Organization to verify everything is working correctly***.
**Disclaimer**: As of 2020-01-15, configuring and reading the AWS Health Organizational View API is **only** done via API calls. In other words, you can NOT see entries and/or status in the console. Also, ***AWS Health Organizational View Alerts only starts working once you enable it (Step 1 below), which means any events that occurred before enabling, will not get added. You will need to wait for a Health event to happen to one of the accounts in your AWS Organization to verify everything is working correctly***.
1. The first thing you will need to do is enable [AWS Organization Health Service Access](https://docs.aws.amazon.com/health/latest/APIReference/API_EnableHealthServiceAccessForOrganization.html).  To do so, you need to have python (at least 3.6) and the following packages installed: `awscli` and `boto3 (at least 1.10.45)`. Configure `awscli` for your AWS Organization Master account, instructions are [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html). Once configured, run the command `aws health enable-health-service-access-for-organization`, to verify it worked run `aws health describe-health-service-status-for-organization`. You should get a response back that says `"healthServiceAccessStatusForOrganization": "ENABLED"`. **Remember, only Health events that occurred from this point forward will be sent to Amazon Chime**.
2. In the folder `chime-version` you will find three files you will need: `CFT_chime-version.yml`, `healthapi-chime.zip` and `updated-boto3.zip`.   
3. Upload `healthapi-chime.zip` and `updated-boto3.zip` to S3 in the same region you plan to deploy this in.   
4. In your AWS console go to *CloudFormation*.   
4. In the *CloudFormation* console **click** *Create stack > With new resources (standard)*.   
5. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_chime-version.yml` **Click** *Next*.   
6. -In *Stack name* type a stack name (i.e. AHOVAChime).   
-In *Lambda Bucket* type ***just*** the name of the S3 bucket that contains `healthapi-chime.zip` (i.e. my-bucket-name).     
-In *Lambda Key* type ***just*** the location of the `healthapi-chime.zip` (i.e. if in root bucket, healthapi-chime.zip or in a folder, foldername/healthapi_chime.zip).   
-In *Layer Bucket* type ***just*** the name of the S3 bucket that contains `updated-boto3.zip`.   
-In *Layer Key* type ***just*** the location of the `updated-boto3.zip`.   
-In *ttl* you can leave it default which will search back 4 hours each time (or change it to something bigger/smaller).     
-In *Regions* leave it blank to search all regions or enter in a comma separated list of specific regions you want to alert on (i.e. us-east-1,us-east-2).   
-In *ChimeURL* put in the *Webhook URL* you got from *Step 5* in the [Create Incoming Amazon Chime Webhook](#create-incoming-amazon-chime-webhook) ***(without https:// in front)***. **Click** *Next*.
7. Scroll to the bottom and **click** *Next*.   
8. Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.   
9. Wait until *Status* changes to *CREATE_COMPLETE* (roughly 5-10 minutes).   
10. Unless you received an event on one of your AWS Organization accounts ***after*** you enabled the service in step 1, you will not get any notifications until an event occurs.

## AHOVA for Slack  

### Create Incoming Slack Webhook
Before you start you will need to create a Slack Webhook URL that the Lambda will be posting to. Within the architecture this webhook will be encrypted automatically. **You will need to have access to add a new channel and app to your Slack Workspace**.

1. Create a new [channel](https://slack.com/help/articles/201402297-Create-a-channel) for events (i.e. aws_events)
2. In your browser go to: workspace-name.slack.com/apps where workspace-name is the name of your Slack Workspace.   
3. In the search bar, search for: *Incoming Webhooks* and **click** on it.   
4. **Click** on *Add to Slack*.   
5. From the dropdown **click** on the channel your created in step 1 and **click** *Add Incoming Webhooks integration*.   
6. From this page you can change the name of the webhook (i.e. AWS Bot), the icon/emoji to use, etc.   
7. For the deployment we will need the *Webhook URL*.

### Install AHOVA for Slack
**Disclaimer**: As of 2020-01-15, configuring and reading the AWS Health Organizational View API is **only** done via API calls. In other words, you can NOT see entries and/or status in the console. Also, ***AWS Health Organizational View Alerts only starts working once you enable it (Step 1 below), which means any events that occurred before enabling, will not get added. You will need to wait for a Health event to happen to one of the accounts in your AWS Organization to verify everything is working correctly***.
1. The first thing you will need to do is enable [AWS Organization Health Service Access](https://docs.aws.amazon.com/health/latest/APIReference/API_EnableHealthServiceAccessForOrganization.html).  To do so, you need to run have python and the following packages installed: `awscli` and `boto3 (at least 1.10.45)`. Configure `awscli` for your AWS Organization Master account, instructions are [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html). Once configured, run the command `aws health enable-health-service-access-for-organization`, to verify it worked run `aws health describe-health-service-status-for-organization`. You should get a response back that says `"healthServiceAccessStatusForOrganization": "ENABLED"`. **Remember, only Health events that occurred from this point forward will be sent to Slack**.
2. In the folder `org-version` you will find three files you will need: `CFT_org-version.yml`, `healthapi-slack.zip` and `updated-boto3.zip`.   
3. Upload `healthapi-slack.zip` and `updated-boto3.zip` to S3 in the same region you plan to deploy this in.   
4. In your AWS console go to *CloudFormation*.   
4. In the *CloudFormation* console **click** *Create stack > With new resources (standard)*.   
5. Under *Template Source* **click** *Upload a template file* and **click** *Choose file*  and select `CFT_healthapi-version.yml` **Click** *Next*.   
6. -In *Stack name* type a stack name (i.e. AHOVASlack).   
-In *Lambda Bucket* type ***just*** the name of the S3 bucket that contains `healthapi-slack.zip` (i.e. my-bucket-name).   
-In *Lambda Key* type ***just*** the location of the `healthapi-slack.zip` (i.e. if in root bucket, sns-slack.zip or in a folder, foldername/sns-slack.zip).   
-In *Layer Bucket* type ***just*** the name of the S3 bucket that contains `updated-boto3.zip`.   
-In *Layer Key* type ***just*** the location of the `updated-boto3.zip`.   
-In *EnvTimeToLiveSeconds* you can leave it default which will search back 4 hours each time (or change it to something bigger/smaller).   
-In *Regions* leave it blank to search all regions or enter in a comma separated list of specific regions you want to alert on (i.e. us-east-1,us-east-2).   
-In *SlackURL* put in the *Webhook URL* you got from *Step 7* in the [Webhook Instructions](#create-incoming-slack-webhook) ***(without https:// in front)***. **Click** *Next*.   
7. Scroll to the bottom and **click** *Next*.   
8. Scroll to the bottom and **click** the *checkbox* and **click** *Create stack*.   
9. Wait until *Status* changes to *CREATE_COMPLETE* (roughly 5-10 minutes).   
10. Unless you received an event on one of your AWS Organization accounts ***after*** you enabled the service in step 1, you will not get any notifications until an event occurs.

# Troubleshooting
* If for whatever reason you need to update the Webhook URL. Just update the CloudFormation Template with the new Webhook URL (minus the https:// of course) and the KMSEncryptionLambda will encrypt the new Webhook URL and update the DecryptionLambda.
* If you are expecting an event and it did not show up it may be an oddly formed event. Take a look at CloudWatch > Log groups and look at the Lambda that sends to Chime/Slack.  See what the error is and reach out to me via [email](mailto:jordroth@amazon.com) for help.