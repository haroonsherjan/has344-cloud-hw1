import json
import datetime
import time
import os
import dateutil.parser
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def send_recommendations(intent_request):
    client = boto3.client('sqs')
    slots = intent_request['currentIntent']['slots']
    searchParameters = intent_request['sessionAttributes']['SearchParameters']
    cuisine = try_ex(lambda: slots['Cuisine'])
    numberOfPeople = try_ex(lambda: slots['NumberOfPeople'])
    diningTime = try_ex(lambda: slots['DiningTime'])
    phoneNumber = try_ex(lambda: slots['PhoneNumber'])
    location = try_ex(lambda: slots['Location'])
    date = try_ex(lambda: slots['Date'])
    response = client.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/537749218305/conciergeQueue.fifo',
        MessageBody=searchParameters,
        MessageGroupId='1'
    )
    print(response)


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def isvalid_city(location):
    valid_cities = ["Manhattan", "Brooklyn", "Los Angeles", "San Francisco", "Austin", "Houston", "Chicago", "Boston",
                    "Portland", "Phoenix", "Sacramento", "New Orleans"]
    return location.title() in valid_cities


def isvalid_cuisine(cuisine):
    valid_cuisines = ['mexican', 'italian', 'indian', 'chinese', 'japanese', 'french', 'brazilian', 'moroccan',
                      'korean', 'german', 'african', "pizza"]
    return cuisine.lower() in valid_cuisines


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def is_after_now(date, time):
    return (dateutil.parser.parse(date).date() > datetime.date.today()) or (
            dateutil.parser.parse(date).date() == datetime.date.today() and dateutil.parser.parse(
        time).time() > datetime.datetime.now().time())


def is_today_or_later(date):
    return (dateutil.parser.parse(date).date() >= datetime.date.today())


def isvalid_phone(phone):
    return len(phone) == 10


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_restaurant_slots(slots):
    cuisine = try_ex(lambda: slots['Cuisine'])
    numberOfPeople = safe_int(try_ex(lambda: slots['NumberOfPeople']))
    location = try_ex(lambda: slots['Location'])
    diningTime = try_ex(lambda: slots['DiningTime'])
    phoneNumber = try_ex(lambda: slots['PhoneNumber'])
    date = try_ex(lambda: slots['Date'])

    if location and not isvalid_city(location):
        return build_validation_result(
            False,
            'Location',
            'We currently do not support {} as a valid destination.  Can you try a different city, such as Manhattan or Brooklyn?'.format(
                location)
        )

    if date:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand your date request.')
        if not is_today_or_later(date):
            return build_validation_result(False, 'Date',
                                           'Suggestions cannot be given for a past date.  Can you try a different date?')
    if date and diningTime:
        if not is_after_now(date, diningTime):
            return build_validation_result(False, 'DiningTime',
                                           'Suggestions cannot be given for a past time. Can you try a different time today?')

    if numberOfPeople and (numberOfPeople < 1 or numberOfPeople > 10):
        return build_validation_result(
            False,
            'NumberOfPeople',
            'I can only make suggestions for between 1 and 10 people. Can you provide a different group size?'
        )

    if cuisine and not isvalid_cuisine(cuisine):
        return build_validation_result(
            False,
            'Cuisine',
            'Unfortunately, I don\'t know any good restaurants for that cuisine. Is there a different cuisine you would like to try?'
        )

    if phoneNumber and not isvalid_phone(phoneNumber):
        return build_validation_result(
            False,
            'PhoneNumber',
            'Please provide your phone number in the standard 10 digit format for the USA.'
        )

    return {'isValid': True}


def dining_suggestions(intent_request):
    """
    Performs dialog management and fulfillment for booking a car.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    slots = intent_request['currentIntent']['slots']
    cuisine = try_ex(lambda: slots['Cuisine'])
    numberOfPeople = try_ex(lambda: slots['NumberOfPeople'])
    diningTime = try_ex(lambda: slots['DiningTime'])
    phoneNumber = try_ex(lambda: slots['PhoneNumber'])
    location = try_ex(lambda: slots['Location'])
    date = try_ex(lambda: slots['Date'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    searchParameters = json.dumps({
        'Cuisine': cuisine,
        'NumberOfPeople': numberOfPeople,
        'DiningTime': diningTime,
        'PhoneNumber': phoneNumber,
        'Location': location,
        'Date': date
    })
    session_attributes['SearchParameters'] = searchParameters

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_restaurant_slots(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        send_recommendations(intent_request)

    # Return
    logger.debug('searchParameters: {}'.format(searchParameters))
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'You\'re all set. Expect my suggestions shortly.'
        }
    )


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug(
        'dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions(intent_request)
    else:
        return delegate(intent_request['session_attributes'], intent_request['currentIntent']['slots'])

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    print(event)
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
