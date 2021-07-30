import json
import boto3

iot = boto3.client('iot-data')
dynamodb = boto3.client('dynamodb')

TABLE_NAME = "LCM"
DEFAULT_TRANSITION_TIME = 2
QOS = 0
LAMP_DIM_LEVEL_RANGE = [0,1000]
message = {}
mqtt_topic = "idt/lcm/{ipv6}/dim"

# keys are used in python code
# values are used in http and mqtt
# index 0 is http, index 1 is mqtt
http_mqtt_mapping = { 
    "level": ["level","level"],
    'transition-time': ['transition-time','time']
    } 

def set_dim(event, context):
    """Check the where the dim command has to be routed and then route it to the correct hub.
    
    Parameters
    ----------
    event : dict
        details related to html request

    context:
        object provides methods and properties that provide information about the invocation, function, and execution environment
        for more details visit:
        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    -------
    json
        a response in a form of json
    """
    print(event)

    path = event["path"]
    ipv6 = path.split("/",4)[3]
    # hubs = check_parent_hub(ipv6)
    
    print(type(event['body']))
    print(f"body: {event['body']}")
    event["body"].replace("\n ","")
    body = json.loads(event["body"])
    
    response = validate_body(body)

    print(f"generated mqtt message: {message}")
    mt = mqtt_topic.replace("{ipv6}",ipv6)
    print("mqtt_topc: "+ mt)
    if response["status"] == 200:
        # print(hubs)
        iot.publish(
            topic= mt,
            qos=QOS,
            payload=json.dumps(message))

        return build_response(200,"Success")
    else:
        return build_response(response["status"],response["message"])
    

    
def check_parent_hub(lamp: str) -> str:
    """Return the hub associated with the lamp.
    
    Parameters
    ----------
    hub : str
        IPv6 address of the lamp. eg. fe70::200:ad10:20:12d5

    Returns
    -------
    str
        a hubid to which the lamp is associsted
    """

    result = dynamodb.get_item(TableName=TABLE_NAME, Key={
        "ip": {
            "S": lamp
        }
    })
    
    return result['Item']['hubid']['S']
    

def build_response(statusCode: int,message: str) -> dict:
    """Build and return response according to status code and message
    
    Parameters
    ----------
    statusCode: int
        status code for response. eg. 404
        
    message: str
        response message for genreate eg. Resourse Not Found

    Returns
    -------
    dict
        response
    """
    return  {
                'statusCode': statusCode,
                'body': json.dumps({
                    "message": message
                }),
                "headers": {
                    "Access-Control-Allow-Origin" : "*",
                    "Accept" : "application/json"
                }
            }



def validate_body(body: dict) -> dict:
    """Validate the body of the http request.
    
    Parameters
    ----------
    body : dict
        body of the http reqeust

    Returns
    -------
    dict
        a dict object with "status" and "message"
        "status": int 
            possible codes: 200,400; look for http status codes for more details
        "message": str
            message pertaining failure or success
    """
    http_lvl = http_mqtt_mapping["level"][0]
    if http_lvl in body:
        if type(body[http_lvl]) is int or type(body[http_lvl]) is float:
            body[http_lvl] = float(body[http_lvl])
            if body[http_lvl] < 0 or body["level"] > 100:
                msg = "Field '"+str(http_lvl)+"' expects value between: 0-100"
                return { "status": 400, "message": msg}
        elif type(body[http_lvl]) is str:
            try:
                body[http_lvl] = float(body[http_lvl])
            except ValueError:
                msg = "Field '"+ str(http_lvl) +"' expects 'integer or decimal' data!"
                return { "status": 400, "message": msg}
        else:
            msg = "Field '"+ str(http_lvl) +"' expects 'integer or decimal' data!"
            return { "status": 400, "message": msg}

        calculted_dim_lvl = (body[http_lvl]*(LAMP_DIM_LEVEL_RANGE[1] - LAMP_DIM_LEVEL_RANGE[0])/100) + LAMP_DIM_LEVEL_RANGE[0]
        calculted_dim_lvl = int(calculted_dim_lvl)
        message[http_mqtt_mapping["level"][1]] = calculted_dim_lvl
    else:
        return {"status": 400, "message": f"Field '{http_lvl}' missing in request body!"}
    
    if http_mqtt_mapping['transition-time'][0] in body:
        if type(body[http_mqtt_mapping['transition-time'][0]]) is int:
            message[http_mqtt_mapping['transition-time'][1]] = body[http_mqtt_mapping['transition-time'][0]]
        else:
            return {"status": 400, "message": f"Field '{http_mqtt_mapping['transition-time'][0]}' missing in request body!"}
    else:
        message[http_mqtt_mapping['transition-time'][1]] = DEFAULT_TRANSITION_TIME

    return {"status": 200, "message":"success"}