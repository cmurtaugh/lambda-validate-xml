from __future__ import print_function

import json
import urllib
import boto3
from lxml import etree
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

s3 = boto3.client('s3')
sns = boto3.client('sns')
sqs = boto3.resource('sqs')
dynamodb = boto3.client('dynamodb')

schema_file = './CourseFeed.xsd'
with open(schema_file, 'r') as f:
    schema_root = etree.XML(f.read())
schema = etree.XMLSchema(schema_root)


def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event, indent=2))

    logger.info("Function/version: %s/%s", context.function_name, context.function_version)
    dynamo_config = dynamodb.get_item(TableName='configuration', Key={'application': {'S': context.function_name}})
    sns_topic = dynamo_config['Item']['sns_topic']['S']
    queue_name = dynamo_config['Item']['queue_name']['S']
    school_ids = dynamo_config['Item']['school_ids']['SS']

    # Get the uploaded object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))

    # make sure the key looks normal
    try:
        # the key should have two parts separated by a /
        (school_id, filename) = key.split('/')
        if school_id not in school_ids:
            logger.error("Key path doesn't match valid school IDs: %s", key)
            return False
    except ValueError:
        # this will be thrown if the key doesn't split into two parts
        logger.error("Uploaded file key format is incorrect: %s", key)
        return False

    # make sure the file is XML and validates against the schema
    is_valid, errmsg = check_file(bucket, key)
    if is_valid:
        logger.info('Document %s/%s is valid.', bucket, key)
        # move the file to the archive bucket
        new_bucket, new_key = move_to_archive(bucket, key)
        logger.info('Successfully moved from %s/%s to %s/%s', bucket, key, new_bucket, new_key)
        # queue the file for import
        message_id = queue_import_job(queue_name, new_bucket, new_key, school_id)
        logger.info('Queued job %s for import of %s/%s', message_id, new_bucket, new_key)
        # notify the user
        sns.publish(
            TopicArn=sns_topic,
            Subject='Successfully queued /{} for import'.format(key),
            Message='Feed file /{} has been received, validated, and queued for import. The message ID for this queued job is {}.'.format(key, message_id),
        )
        return True
    else:
        logger.error("XML document is invalid! {}".format(errmsg))
        sns.publish(
            TopicArn=sns_topic,
            Subject='ERROR validating /{}'.format(key),
            Message='Feed file /{} failed validation: {}'.format(key, errmsg),
        )
        return False


def check_file(bucket, key):
    try:
        uploaded_xml = s3.get_object(Bucket=bucket, Key=key)
    except Exception as e:
        return False, "Could not retrieve file {} from bucket for validation: {}".format(key, bucket, e)

    # make sure what we have is an XML file
    if uploaded_xml['ContentType'] != 'application/xml':
        return False, "Uploaded file content type '{}' doesn't match 'application/xml'".format(uploaded_xml['ContentType'])

    # validate the XML
    try:
        doc = etree.parse(uploaded_xml['Body'])
        schema.assertValid(doc)
        return True, None

    except etree.DocumentInvalid as xsde:
        return False, str(xsde)


def move_to_archive(bucket, key):
    # move the file to the archive bucket and give it a unique filename
    new_key = '/'.join([key.split('/')[0], time.strftime("%Y%m%d-%H%M%S")])
    new_bucket = bucket.replace('dropbox', 'archive')
    s3.copy_object(CopySource='/'.join([bucket, key]), Bucket=new_bucket, Key=new_key)
    logger.debug("successfully copied to {}/{}".format(new_bucket, new_key))

    # then delete it from the dropbox
    s3.delete_object(Bucket=bucket, Key=key)
    logger.debug("successfully deleted old file {}/{}".format(bucket, key))
    return new_bucket, new_key


def queue_import_job(queue_name, bucket, key, school_id):
    # may eventually set up separate queues per school...
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    message = queue.send_message(
        MessageBody='/'.join([bucket, key]),
        MessageAttributes={
            'bucket': {
                'StringValue': bucket,
                'DataType': 'String'
            },
            'key': {
                'StringValue': key,
                'DataType': 'String'
            },
            'school_id': {
                'StringValue': school_id,
                'DataType': 'String'
            },
        }
    )
    logger.debug(json.dumps(message, indent=2))
    return message['MessageId']


# test it:

# move_to_archive('hds', 'uw-feed-dropbox-qa', 'hds/hds-fall-courses.xml')
# check_file('uw-feed-dropbox-qa', 'hls/hls_courses.xml')
# queue_import_job('testbucket', 'sch/test.xml')
