def validate_body(body: dict, schema: dict) -> dict:
    """Validate the body of the http request.
    
    Parameters
    ----------
    body : dict
        body of the http reqeust

    schema: dict
        schema of the http request body

    Returns
    -------
    dict
        a dict object with "status" and "message"
        "status": int 
            possible codes: 200,400; look for http status codes for more details
        "message": str
            message pertaining failure or success
    """
    report = {
        "statusCode": 1
    }

    extra_values = []
    type_mismatch = []
    illigal_value = []
    missing_fields = []
    collectExtra = False


    if "removeExtraValues" in schema:
        remove_extra_values = schema.pop("removeExtraValues")
        if "collectExtraValues" in schema:
            collectExtra = schema.pop("collectExtraValues")
        if type(remove_extra_values) == bool:
            extra_values = extranuous_fields(body, schema, extra_values,remove_extra_values)
        else:
            print("Illigal value for removeExtraValue expected bool found", type(remove_extra_values),"\n using default value")
            extra_values = extranuous_fields(body, schema, extra_values)
    else:
        if "collectExtraValues" in schema:
            collectExtra = schema.pop("collectExtraValues")
            if collectExtra == True:
                extranuous_fields(body, schema, extra_values)

    missing_required_fields(body, schema, missing_fields)
    type_value_checking(body, schema, type_mismatch, illigal_value, missing_fields, report)

    # print("Extra values",extra_values)
    if collectExtra and len(extra_values) != 0:
        report["extraValues"] = extra_values
        report["statusCode"] = 2

    # print("type mismatch",type_mismatch)
    if len(type_mismatch) != 0:
        report["typeMismatch"] = type_mismatch
        report["statusCode"] = 0

    # print("missing fields",missing_fields)
    if len(missing_fields) != 0:
        report["missingValues"] = missing_fields
        report["statusCode"] = 0

    # print("illigal values",illigal_value)
    if len(illigal_value) != 0:
        report["illigalValues"] = illigal_value
        report["statusCode"] = 0

    # print("This is the end report", report)

    return report



def extranuous_fields(body: dict, schema: dict, extra_values: list,removeExtraValues = False) -> list:
    """Validate the body of the http request.
    
    Parameters
    ----------
    body : dict
        body of the http reqeust

    schema: dict
        schema of the http request body

    removeExtraValues: boolean
        removes any extra value whaich has been provided not in schema
    """
    bkeys  = body.keys()

    for bkey in bkeys:
        if not bkey in schema:
            extra_values = add_warning("extra_value",bkey, extra_values)

    if removeExtraValues:
        for key in extra_values:
            body.pop(key)

    return extra_values



def missing_required_fields(body: dict, schema: dict, logger: list):
    for key in schema.keys():
        if schema[key]["require"]:
            if not (key in body):
                add_warning("missing_value", key, logger)



def type_value_checking(body: dict, schema: dict, type_mismatch: list, illigal_value: list, missing_fields: list, report: dict):
    skeys = schema.keys()
    bkeys = body.keys()

    for skey in skeys:
        if schema[skey]["type"] == "str":
            string_type_check(body, schema, skey, type_mismatch, illigal_value, missing_fields)
        elif schema[skey]["type"] == "int":
            int_type_check(body, schema, skey, type_mismatch, illigal_value, missing_fields)
        elif schema[skey]["type"] == "float":
            float_type_check(body, schema, skey, type_mismatch, illigal_value, missing_fields)
        elif schema[skey]["type"] == "dict":
            if not skey in missing_fields:
                if skey in body:
                    if type(body[skey]) == dict:
                        if "content" in schema[skey]:
                            repo = validate_body(body[skey],schema[skey]["content"])
                            if repo["statusCode"] == 0:
                                report["statusCode"] = 0
                                repo.pop("statusCode")
                                report[skey] = repo
                            elif repo["statusCode"] == 2:
                                repo.pop("statusCode")
                                if report["statusCode"] == 1:
                                    report["statusCode"] = 2
                                report[skey] = repo
                    else:
                        add_warning("type_mismatch", skey, type_mismatch,"dict",type(body[skey]))
        elif schema[skey]["type"] == "list":
            list_content_check(body, schema, skey, type_mismatch, illigal_value, missing_fields, report)
        else:
            return

def list_content_check(body: dict, schema: dict, skey: str, type_mismatch: list, illigal_value: list, missing_fields: list, report: dict):
    if not skey in missing_fields:
        if skey in body:
            if type(body[skey]) == list:
                if "contentType" in schema[skey]:
                    if schema[skey]["contentType"] == "dict":
                        for element in body[skey]:
                            if type(element) == dict:
                                if "content" in schema[skey]:
                                    repo = validate_body(body[skey],schema[skey]["content"])
                                    if repo["statusCode"] == 0:
                                        report["statusCode"] = 0
                                        repo.pop("statusCode")
                                        report[skey] = repo
                                    elif repo["statusCode"] == 2:
                                        repo.pop("statusCode")
                                        if report["statusCode"] == 1:
                                            report["statusCode"] = 2
                                        report[skey] = repo
                            else:
                                add_warning("type_mismatch", skey, type_mismatch,"dict",type(body[skey]))
            else:
                add_warning("type_mismatch", skey, type_mismatch,"str",type(body[skey]))



def string_type_check(body: dict, schema: dict, skey: str, type_mismatch: list, illigal_value: list, missing_fields: list):
    if not skey in missing_fields:      # missing field only contains keys which are required and are missing
        if skey in body:    # checking the optional key is present in the body
            if type(body[skey]) == str:     # checking type of the value present in the body 
                legal_value_range_check(body, schema, skey, illigal_value)
            elif type(body[skey]) == int or type(body[skey]) == float:
                if "strictTypeCheck" in schema[skey]:
                    if not schema[skey]["strictTypeCheck"]:
                        body[skey] = str(body[skey])
                        legal_value_range_check(body, schema, skey, illigal_value)
                    else:
                        add_warning("type_mismatch", skey, type_mismatch,"str",type(body[skey]))
                else:
                    add_warning("type_mismatch", skey, type_mismatch,"str",type(body[skey]))
            else:
                add_warning("type_mismatch", skey, type_mismatch,"str",type(body[skey]))



def int_type_check(body: dict, schema: dict, skey: str, type_mismatch: list, illigal_value: list, missing_fields: list):
     if not skey in missing_fields:      # missing field only contains keys which are required and are missing
        if skey in body:    # checking the optional key is present in the body
            if type(body[skey]) == int:     # checking type of the value present in the body 
                legal_value_range_check(body, schema, skey, illigal_value)
            elif type(body[skey]) == str or type(body[skey]) == float:
                if "strictTypeCheck" in schema[skey]:
                    if not schema[skey]["strictTypeCheck"]:
                        try:
                            body[skey] = int(body[skey])
                            legal_value_range_check(body, schema, skey, illigal_value)
                        except Exception:
                            add_warning("type_mismatch", skey, type_mismatch,"int",type(body[skey]))
                    else:
                        add_warning("type_mismatch", skey, type_mismatch,"int",type(body[skey]))
                else:
                    add_warning("type_mismatch", skey, type_mismatch,"int",type(body[skey]))
            else:
                add_warning("type_mismatch", skey, type_mismatch,"int",type(body[skey]))
        else:
            if "defaultValue" in schema[skey]:
                body[skey] = schema[skey]["defaultValue"]

def float_type_check(body: dict, schema: dict, skey: str, type_mismatch: list, illigal_value: list, missing_fields: list):
    if not skey in missing_fields:      # missing field only contains keys which are required and are missing
        if skey in body:    # checking the optional key is present in the body
            if type(body[skey]) == float or type(body[skey]):     # checking type of the value present in the body 
                body[skey] = float(body[skey])
                legal_value_range_check(body, schema, skey, illigal_value)
            elif type(body[skey]) == str:
                if "strictTypeCheck" in schema[skey]:
                    if not schema[skey]["strictTypeCheck"]:
                        try:
                            body[skey] = int(body[skey])
                            legal_value_range_check(body, schema, skey, illigal_value)
                        except Exception:
                            add_warning("type_mismatch", skey, type_mismatch,"float",type(body[skey]))
                    else:
                        add_warning("type_mismatch", skey, type_mismatch,"float",type(body[skey]))
                else:
                    add_warning("type_mismatch", skey, type_mismatch,"float",type(body[skey]))
            else:
                add_warning("type_mismatch", skey, type_mismatch,"float",type(body[skey]))
        else:
            if "defaultValue" in schema[skey]:
                body[skey] = schema[skey]["defaultValue"]



def legal_value_range_check(body: dict, schema: dict, skey: str, logger: list):
    if "legalValues" in schema[skey]:       # checking if the list of the legal values are mentioned in the schema
        if "strictValueCheck" in schema[skey] and schema[skey]["strictValueCheck"] == True:
            if not body[skey] in schema[skey]["legalValues"]:
                add_warning("illigal_value", skey, logger, schema[skey]["legalValues"], body[skey])
        else:
            if not body[skey] in schema[skey]["legalValues"]:
                if not "defaultValue" in schema[skey]:
                    add_warning("illigal_value", skey, logger, schema[skey]["legalValues"], body[skey])
                else:
                    body[skey] = schema[skey]["defaultValue"]
    elif "range" in schema[skey]:   #checking of range is provided for a value
        if "strictValueCheck" in schema[skey] and schema[skey]["strictValueCheck"] == True:
            if not (body[skey] > schema[skey]["range"][0] and body[skey] < schema[skey]["range"][1]):
                add_warning("illigal_range", skey, logger, schema[skey]["range"], body[skey])
        else:
            if body[skey] < schema[skey]["range"][0]:
                body[skey] = schema[skey]["range"][0]
            elif body[skey] > schema[skey]["range"][1]:
                body[skey] = schema[skey]["range"][1]
    elif "defaultValue" in schema[skey]:
        if not body[skey]:
            body[skey] = schema[skey]["defaultValue"]





def add_warning(type: str, skey, logger: list,expected=None, found=None) -> list:
    """Validate the body of the http request.
    
    Parameters
    ----------
    type : str
        type of warning: 
            "type_mismatch": when there is mismatch of the type
            "illigal_value": when the value is not the correct value
            "extra_value": any value which is not specified in schema
            "missing_value": any missing required value

    skey: 
        key associated with the problem

    expected: 
        Type of value expected for skey
        This is required when type is "type_mismatch" or "illigal_value"

    found: 
        Type of value found for skey
        This is required when type is "type_mismatch" or "illigal_value"
    """

    if type == "type_mismatch":
        logger.append({
            skey: {
                "expected": expected,
                "found": found
            }
        })

    elif type == "illigal_value":
        logger.append({
            skey: {
                "expected": expected,
                "found": found
            }
        })

    elif type == "illigal_range":
        logger.append({
            skey: {
                "expected": {
                    "min_value": expected[0],
                    "max_value": expected[1]
                },
                "found": found
            }
        })

    elif type == "extra_value":
        logger.append(skey)

    elif type == "missing_value":
        logger.append(skey)

    else:
        print("You have reached warning logger in unreachable part:", type)

    return logger