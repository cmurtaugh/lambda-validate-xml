from __future__ import print_function

import json
import urllib
import boto3
from lxml import etree

print('Loading function')

s3 = boto3.client('s3')

schema_file = './CourseFeed.xsd'
with open(schema_file, 'r') as f:
    schema_root = etree.XML(f.read())
schema = etree.XMLSchema(schema_root)


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response['ContentType'])

        # validate the XML
        (is_valid, errmsg) = validate_xml(response['Body'])
        if is_valid:
            print("XML document is valid!")
        else:
            print("ERROR: XML document is invalid! {}".format(errmsg))

        return response['ContentType']

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e


def validate_xml(filedata):
    try:
        doc = etree.parse(filedata)
        schema.assertValid(doc)
        return True, None

    except etree.DocumentInvalid as xsde:
        print('XMLSchemaError: {}'.format(xsde))
        return False, str(xsde)

    except etree.XMLSyntaxError as e:
        print('XMLSyntaxError: {}'.format(e.msg))
        return False, str(e)
