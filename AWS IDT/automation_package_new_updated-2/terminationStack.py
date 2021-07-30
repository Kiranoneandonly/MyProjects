import boto3
import sys
import time
import csv

sys.stdout = open('log.txt', 'w')
userBucket = ""
location = 'us-west-2'

# sys.argv = ['aws-test-direct1', 'aws-test-direct2', 'E:\/6. AWS_ICE_project\/automation_package_new_updated\credentials-kasturi.csv']

if len(sys.argv) == 0:
    print("user needs to enter a unique buketname")
    exit()
else:
    userBucket = str(sys.argv[1])

if len(sys.argv) == 0 or str(sys.argv[2]) == "":
    print("user needs to select credentials file", flush=True)
    exit()
else:
    credentials_path = str(sys.argv[2])
    print("user credential: " + credentials_path, flush=True)

credentials_list = []
with open(credentials_path) as f:
    credentials_list = [{k: str(v) for k, v in row.items()}
         for row in csv.DictReader(f, skipinitialspace=True)]

access_key_id = credentials_list[0]["Access key ID"]
secret_access_key = credentials_list[0]["Secret access key"]

s3Client = boto3.resource('s3', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
                          region_name=location)
cloudFormationClient = boto3.client('cloudformation', aws_access_key_id=access_key_id,
                                    aws_secret_access_key=secret_access_key, region_name=location)

userBucketCode = userBucket + "-code"

print("user clients created", flush=True)


def delete_buckets(bucket):
    try:
        bucket = s3Client.Bucket(bucket)
        bucket.objects.all().delete()
        bucket.delete()
    except Exception as e:
        print("Bucket already deleted", flush=True)

delete_buckets(userBucket)
delete_buckets(userBucketCode)
delete_buckets(userBucket+"-cf-template-stack")

print("finished deleting buckets " + userBucket, flush=True)


try:
    resonse = cloudFormationClient.delete_stack(StackName='streetLightStack')
    print("Delete stack initiated", flush=True)
except Exception as e:
    print("Error deleting cloudformation stack. Check the web console")

time.sleep(70)
print("finished deleting stack", flush=True)
