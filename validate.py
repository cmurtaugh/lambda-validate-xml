#!/usr/bin/env python

import glob
from lxml import etree

schema_file = './CourseFeed.xsd'


def validate(xmlfilename):
    with open(schema_file, 'r') as f:
        schema_root = etree.XML(f.read())

    schema = etree.XMLSchema(schema_root)
    print "Schema_root is {}".format(schema_root)
    # xmlparser = etree.XMLParser()
    try:
        with open(xmlfilename, 'r') as f:
            doc = etree.parse(f)
            schema.assertValid(doc)
        return True
        
    except etree.DocumentInvalid as xsde:
        print 'XMLSchemaError: {}'.format(xsde)
        return False

    except etree.XMLSyntaxError as e:
        print 'XMLSyntaxError: {}'.format(e.msg)
        return False

filenames = glob.glob('*.xml')


for filename in filenames:
    if validate(filename):
        print "******  %s validates *******" % filename
    else:
        print "%s doesn't validate" % filename
