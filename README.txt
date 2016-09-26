
Process for packaging this Lambda function for installation on AWS:

- log into amazon linux server
- check out the code (this directory)

- make sure that the following RPMs are installed:
  gcc
  libxml2
  libxml2-devel
  libxslt
  libxslt-devel



- create the zip

zip -9 ~/lambda-validate-xml.zip xmlfeed_validate_and_queue.py
zip -9 ~/lambda-validate-xml.zip CourseFeed.xsd

cd ~/.virtualenvs/lambda-validate-xml/lib/python2.7/site-packages/
zip -r9 ~/lambda-validate-xml.zip *

cd ~/.virtualenvs/lambda-validate-xml/lib64/python2.7/site-packages/
zip -r9 ~/lambda-validate-xml.zip *


- update the function

e.g.:
aws lambda update-function-code --function-name xmlfeed_validate_and_queue_qa --zip-file fileb://lambda-validate-xml.zip --publish
