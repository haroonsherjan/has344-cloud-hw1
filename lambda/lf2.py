from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import boto3
import random


def getRestaurantIdGivenCuisine(recommendationRequest):
    host = 'search-elastic-yelp-final-hunkmkikl3kafz5esv3cu6v5tu.us-east-1.es.amazonaws.com'  # For example, my-test-domain.us-east-1.es.amazonaws.com
    region = 'us-east-1'  # e.g. us-west-1

    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    es = Elasticsearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    searchBody = {
        "query": {
            "bool": {
                "must": [{
                    "match": {
                        "cuisine": recommendationRequest['Cuisine'].lower()
                    }},
                    {"match": {
                        "city": recommendationRequest['Location'].title()
                    }}
                ]
            }
        }
    }
    response = es.search(index="restaurants", doc_type="restaurant", body=searchBody)
    random.seed()
    print(response)
    total = response['hits']['total']['value']
    hits = response['hits']['hits']
    return random.choice(hits)['_id']


def getRestaurantGivenId(id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    return table.get_item(
        Key={
            'id': id
        }
    )


def sendTextMessage(restaurant, recommendationRequest):
    sns = boto3.client('sns')
    return sns.publish(
        PhoneNumber="+1" + recommendationRequest['PhoneNumber'],
        Message=
        "Hello! Here is a {} restaurant suggestion for {} people, for ".format(
            recommendationRequest['Cuisine'].capitalize(), recommendationRequest['NumberOfPeople']) +
        "{} at {}: ".format(recommendationRequest['Date'], recommendationRequest['DiningTime']) +
        "{}, located at {}. Enjoy your meal!".format(restaurant['Item']['name'], restaurant['Item']['address']
                                                     )
    )


def lambda_handler(event, context):
    print(event)
    recommendationRequest = event['Records'][0]['body']
    if isinstance(recommendationRequest, str):
        recommendationRequest = json.loads(recommendationRequest)
    id = getRestaurantIdGivenCuisine(recommendationRequest)
    restaurant = getRestaurantGivenId(id)
    response = sendTextMessage(restaurant, recommendationRequest)
    # message = json.loads(event['Records'][0]['Sns']['Message'])
    # words = message['messageBody']
    # number = message['originationNumber']
    return {
        'statusCode': 200,
        'body': response
        # 'body': json.dumps("Phone number: {}\nMessage Text: {}".format(number, words))
    }
