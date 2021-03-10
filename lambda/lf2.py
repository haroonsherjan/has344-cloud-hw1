from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import boto3
import random

def getRestaurantIdsGivenCuisine(recommendationRequest):
    host = 'search-elastic-yelp-final-hunkmkikl3kafz5esv3cu6v5tu.us-east-1.es.amazonaws.com' # For example, my-test-domain.us-east-1.es.amazonaws.com
    region = 'us-east-1' # e.g. us-west-1

    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    searchBody = {
        "query": {
            "bool":{
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
    return {random.choice(hits)['_id'], random.choice(hits)['_id'], random.choice(hits)['_id'],
            random.choice(hits)['_id'], random.choice(hits)['_id']}


def getRestaurantsGivenIds(ids):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    restaurants = []
    for id in ids:
        restaurants.append(table.get_item(
            Key ={
                'id': id
            }
        ))
    return restaurants


def sendTextMessage(restaurants, recommendationRequest):
    sns = boto3.client('sns')
    message = 'Hello! Here are some {} restaurant suggestions for {} people, for '.format(recommendationRequest['Cuisine'].capitalize(), recommendationRequest['NumberOfPeople']) + '{} at {}: \n'.format(recommendationRequest['Date'], recommendationRequest['DiningTime'])
    count = 0
    for restaurant in restaurants:
        count = count + 1;
        message = message + "{}. {}, located at {}. ".format(count, restaurant['Item']['name'], restaurant['Item']['address'])
    message = message +  "Enjoy your meal!"
    return sns.publish(
        PhoneNumber= "+1" + recommendationRequest['PhoneNumber'],
        Message=message
    )


def lambda_handler(event, context):
    print(event)
    recommendationRequest = event['Records'][0]['body']
    if isinstance(recommendationRequest, str):
        recommendationRequest = json.loads(recommendationRequest)
    ids = getRestaurantIdsGivenCuisine(recommendationRequest)
    restaurants = getRestaurantsGivenIds(ids)
    response = sendTextMessage(restaurants, recommendationRequest)
    return {
        'statusCode': 200,
        'body': response
    }
