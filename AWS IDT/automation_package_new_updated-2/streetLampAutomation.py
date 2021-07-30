import boto3
import botocore
import os
import mimetypes
import fileinput
from shutil import copy2
import json
import csv
import time
import pyqrcode
import sys 

sys.stdout = open('log.txt', 'w')


def get_template(template, bucket_name):
    print("Creating Stack...", flush=True)
    s3Client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': location})
    print("CF template bucket is created.", flush=True)

    s3Client.upload_file(template, bucket_name, template)
    s3_template_url = "https://s3-" + location + ".amazonaws.com/" + bucket_name + "/" + template
    return s3_template_url


def get_parameters(parameters):
    with open(parameters) as parametersFile:
        parametersData = json.load(parametersFile)
    return parametersData["parameters"]


def upload_files(path,bucketName,session):
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucketName)

    for subdir, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(subdir, file)
            file_mime = mimetypes.guess_type(file)[0] or 'binary/octet-stream'
            with open(full_path, 'rb') as data:
                bucket.put_object(Key=full_path[len(path)+1:].replace('\\','/'), Body=data, ContentType=file_mime)


def print_dots(number,text):
    print(text,end=" ")
    for i in range(number):
        print(".", end='',flush = True)
        time.sleep(3)


def create_stack():
    templateData = get_template("lamdba_deployment_working.json", stackBucket)
    parameters = get_parameters("parameter_cf.json")
    params = {
        'StackName': "streetLightStack",
        'TemplateURL': templateData,
        'Parameters': parameters,
        'Capabilities': [
                'CAPABILITY_IAM',
        ],
    }
    stack_result = cf.create_stack(**params)
    waiter = cf.get_waiter('stack_create_complete')
    print("waiting for stack to be ready...", flush=True)
    waiter.wait(StackName='streetLightStack')
    print("finished stack creation", flush=True)


location = 'us-west-2'
userBucket = "idt"
credentials_path = ""

# sys.argv = ['aws-test-direct1', 'aws-test-direct2', 'E:\/6. AWS_ICE_project\/automation_package_new_updated\credentials-kasturi.csv']
if len(sys.argv) == 0 or str(sys.argv[1]) == "":
    print("user needs to enter a unique bucket name", flush=True)
    userBucket = "kbilgund-idt"
    exit()
else:
    userBucket = str(sys.argv[1])


if len(sys.argv) == 0 or str(sys.argv[2]) == "":
    print("user needs to select credentials file", flush=True)
    exit()
else:
    credentials_path = str(sys.argv[2])
    print("user credential: "+credentials_path,flush=True)


userBucketCode = userBucket+"-code"
stackBucket = userBucket+"-cf-template-stack"
print("user buckets "+userBucket+" "+userBucketCode, flush=True)


with open(credentials_path) as f:
    credentials_list = [{k: str(v) for k, v in row.items()} for row in csv.DictReader(f, skipinitialspace=True)]


access_key_id = credentials_list[0]["Access key ID"]
secret_access_key = credentials_list[0]["Secret access key"]

s3Client = boto3.client('s3', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
cognitoClient = boto3.client('cognito-idp', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
IamClient = boto3.client('iam', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
cf=boto3.client('cloudformation', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
apigatewayv2Client = boto3.client('apigateway', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
session  = boto3.Session(aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=location)
waiter = cf.get_waiter('stack_create_complete')
print("all clients created ")

"""
update the parameters for cloudformation
"""

copy2("parameter_cf_template.json", "parameter_cf.json")
with fileinput.FileInput("parameter_cf.json", inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("\"ParameterValue\":\"idt-street-light\"",
            "\"ParameterValue\":\""+userBucketCode+"\""
            ), end='')

with fileinput.FileInput("parameter_cf.json", inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("\"ParameterValue\":\"idt3\"",
            "\"ParameterValue\":\""+userBucket+"\""
            ), end='')

"""
Create a bucket for the code bundle and upload the code
"""

print("uploading backend files .....", flush=True)
try:
    response = s3Client.create_bucket(Bucket=userBucketCode, CreateBucketConfiguration={'LocationConstraint': location})
except Exception as e:
    print("user needs to enter unique bucket name")
    exit()

upload_files(path="code_bundle", bucketName=userBucketCode, session=session)
print("finished uploading backend files", flush=True)


"""
Run the cloudformation script and wait for the creatation to complete 
"""

create_stack()

"""
Change the config.js before uploading the static web content
"""

print("Uploading front end files .....", flush=True)
configPath = os.path.join("static_website\\js", "config.js")
configTemplatePath = os.path.join("static_website\\js", "config_template.js")
copy2(configTemplatePath, configPath)

userPools = cognitoClient.list_user_pools(MaxResults=5)
userPoolId = ""
for user in userPools["UserPools"]:
    if user["Name"] == "idt-led-cf":
        userPoolId = user['Id']


clientId = ""
userPoolClients = cognitoClient.list_user_pool_clients(UserPoolId=userPoolId, MaxResults=5)
userClientId = ""
for client in userPoolClients["UserPoolClients"]:
    if client["UserPoolId"] == userPoolId:
        clientId = client['ClientId']

with fileinput.FileInput(configPath, inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("userPoolId:", "userPoolId: '"+userPoolId+"',"), end='')
with fileinput.FileInput(configPath, inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("userPoolClientId:", "userPoolClientId: '"+clientId+"',"), end='')


apiGatewayId = ""

restApis = apigatewayv2Client.get_rest_apis(limit=10)
for item in restApis["items"]:
    if item["name"] == "lampAPIcf":
        apiGatewayId=item["id"]

print("got the apigateway", flush=True)

invokeUrl = "https://"+apiGatewayId+".execute-api.us-west-2.amazonaws.com/prod"

with fileinput.FileInput(configPath, inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("invokeUrl:", "invokeUrl:" + "'"+invokeUrl+"'"), end='')

with fileinput.FileInput(configPath, inplace=True, backup='.bak') as file:
    for line in file:
        print(line.replace("bucket_name:", "bucket_name:" + "'"+userBucket+"'"), end='')


"""
Generate the QR code for apigateway
"""

code=pyqrcode.create(invokeUrl)
code.png("static_website\\images\\QR_code" + '.png', scale=6, module_color=[0,0,0,128],quiet_zone=10)


"""
Upload the static Website contents 
"""

upload_files("static_website", userBucket, session=session)
print("finished uploading front end files", flush=True)


"""
Print the results 
"""

print("Register Link : "+"https://s3-"+location+".amazonaws.com/"+userBucket+"/index.html", flush=True)
#print("App Link : "+"https://s3-"+location+".amazonaws.com/"+userBucket+"/android-qr.html", flush=True)
print("DONE - ICE Creation complete")
#print("Please upload this credentials file to the hub "+"\\credentials.csv", flush=True)
