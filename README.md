# Chatbot Concierge #

## S3 Static Website ##
http://has344-hw1.s3-website-us-east-1.amazonaws.com/

## About ##

Restaurant recommendation chatbot made for HW1 of Cloud Computing & Big Data class at NYU.

## Tech Stack ##

1. Javascript front end hosted as static website in S3 bucket
2. AWS API Gateway/Lambda REST API for posting messages to chatbot
3. Amazon Lex chatbot to gather request details for restaurant recommendation
4. DynamoDB pre-populated with restaurant results scraped from YelpFusion API
5. DynamoDB Stream set to populate inserted entries to an ElasticSearch index
6. SQS topic that queues requests and triggers the processing Lambda
7. Lambda function that queries ElasticSearch and DynamoDB for the given cuisine and resulting restaurant PK
8. SNS topic to facilitate SMS notification of final restaurant recommendation

