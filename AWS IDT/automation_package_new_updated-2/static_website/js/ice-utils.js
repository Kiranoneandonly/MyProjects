// Sections
// 1. Configs: Provides default behaviours for calls
// 2. Core Functions: These are low level functions which make direct calls to the ICE
// 3. Wrappers: Higher level functions to call ICE (Please use these function in your code to make calls)
// 3.a. Hub: hub related APIs
// 3.b. Lcm: LCM related APIs

// ==================================== 1. Config ====================================
// These basic configs for calls

function default_on_success() {
    console.log("Success");
}


function default_on_error(jqXHR, textStatus, errorThrown) {
    console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
    console.error('Response: ', jqXHR.responseText);
}


// ==================================== 2. Core Functions ====================================
// These are low level functions which make direct calls to the ICE 

async function getRequest(auth_token, url, on_success, on_error) {
    let dat;
    await $.ajax({
        method: 'GET',
        beforeSend: function (request) {
            request.setRequestHeader('authToken', auth_token);
        },
        url: url,
        crossDomain: true,
        contentType: 'application/json',
        success: on_success(),
        error: function(jqXHR, textStatus, errorThrown){
            on_error(jqXHR, textStatus, errorThrown);
        }
    }).done(function (data) {
        dat = data;
    });
    return dat;
}

async function postRequest(auth_token, url, body, on_success, on_error) {
    let dat;
    await $.ajax({
        method: 'POST',
        beforeSend: function (request) {
            request.setRequestHeader('authToken', auth_token);
        },
        url: url,
        crossDomain: true,
        data: JSON.stringify(body),
        contentType: 'application/json',
        success: on_success(),
        error:function(jqXHR, textStatus, errorThrown){
            on_error(jqXHR, textStatus, errorThrown);
        }
    }).done(function (data) {
        dat = data;
    });
    return dat;
}

async function putRequest(auth_token, url, body, on_success, on_error) {
    let dat;
    await $.ajax({
        method: 'PUT',
        beforeSend: function (request) {
            request.setRequestHeader('authToken', auth_token);
        },
        url: url,
        crossDomain: true,
        data: JSON.stringify(body),
        contentType: 'application/json',
        success: function(data, textStatus, jqXHR){
            if(jqXHR.status==200){
                on_success();
            }
        },
        error: function(jqXHR, textStatus, errorThrown){
            if(jqXHR.status!=200){
                on_error(jqXHR, textStatus, errorThrown);
            }
        }
    }).done(function (data) {
        dat = data;
    });
    return dat;
}

async function deleteRequest(auth_token, url, on_success, on_error) {
    let dat;
    await $.ajax({
        method: 'DELETE',
        beforeSend: function (request) {
            request.setRequestHeader('authToken', auth_token);
        },
        url: url,
        crossDomain: true,
        contentType: 'application/json',
        success: function(data, textStatus, jqXHR){
            console.log(jqXHR.status);
            if(jqXHR.status==200){
                on_success()
            }
        },
        error: function(jqXHR, textStatus, errorThrown){
            on_error(jqXHR, textStatus, errorThrown);
        }
    }).done(function (data) {
        dat = data;
    });
    return dat;
}


// ==================================== 3. Wrappers ====================================
// Description: Higher level functions to call ICE
// Please try use these functions in your code to make calls

// 3.a. Hub

async function getHubs() {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    return await getRequest(authT, _endpoints.rootHub, function () {
        console.log("Get Hubs request Successful")
    }, default_on_error);
}

async function getHub(hubid) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    let url = await _endpoints.hub.replace("{hubid}", hubid);
    return await getRequest(authT, url, function () {
        console.log("Get Hub request Successful");
    }, default_on_error);
}

async function updateHubParams(hubid, params) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    let url = await _endpoints.hub.replace("{hubid}", hubid);
    await putRequest(authT, url, params, function () {
        console.log("Updated Hub params");
    }, default_on_error);
}

async function updateHubGatewaySoftware(hubid, params) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    let url = await _endpoints.hubUpdateGateway.replace("{hubid}", hubid);
    await putRequest(authT, url, params, function () {
        console.log("Request for Gateway update sent");
    }, default_on_error);
}

async function updateHubLCMSoftware(hubid, params) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    let url = await _endpoints.hubUpdateLcm.replace("{hubid}", hubid);
    await putRequest(authT, url, params, function () {
        console.log("Request for Gateway update sent");
    }, default_on_error);
}

// 3.b. Lcm

async function getLamps() {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    return await getRequest(authT, _endpoints.rootLcm, function () {
        console.log("Get Lamps request Successful")
    }, default_on_error);
}

async function getLamp(lcmid) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcm.replace("{lcmid}", lcmid);
    return await getRequest(authT, url, function () {
        console.log("Get Lamp request Successful");
    }, default_on_error);
}

async function addLamp(lcmid, body) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcm.replace("{lcmid}", lcmid);
    await postRequest(authT, url, body, function () {
        console.log("Lamp registered")
        $(".register-success").show();
    }, function (jqXHR, textStatus, errorThrown) {
        console.error('Error toggling address: ', textStatus, ', Details: ',
            errorThrown);
        console.error('Response: ', jqXHR.responseText);
        $("#register-failure").show();
        $("#register-error-content").text(errorThrown);
    });
}

async function deleteLamp(lcmid, on_success, on_error){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    displayUpdate("console",lcmid)
    url = await _endpoints.lcm.replace("{lcmid}", lcmid);
    deleteRequest(authT, url, on_success, on_error);
}

async function setLcmDim(lcmid, body){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmDim.replace("{lcmid}", lcmid);
    return await putRequest(authT, url, body, function () {
        displayUpdate("console", "Lamp dim level has been set to " + body.level);
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming address: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
    });
}

async function getLcmDim(lcmid, query){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmDim.replace("{lcmid}", lcmid);
    url = await url+query;
    return await getRequest(authT, url, function () {
        displayUpdate("console", "Get dim Level request successful");
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming address: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
    });
}

async function setLcmDimRGB(lcmid, body, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmDimrgb.replace("{lcmid}", lcmid);
    onFail = function (jqXHR, textStatus, errorThrown) {
        console.error('Error toggling address: ', textStatus, ', Details: ',
            errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure()
    }
    return await putRequest(authT, url, body, onSuccess, onFail);
}

async function updateLcm(lcmid, body){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmUpdate.replace("{lcmid}", lcmid);
    return await putRequest(authT, url, body, function () {
        displayUpdate("console", "Luminaire update request successful ");
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming address: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
    });
}

async function loadCertifiedLcm(body, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmLoad;
    await postRequest(authT, url, body, function (){
        onSuccess();
    }, function(jqXHR, textStatus, errorThrown){
        console.error('Error dimming address: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure(jqXHR.responseText);
    });
}

async function legacy(body){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    return await putRequest(authT, _endpoints.legacyOnOff, body, default_on_success, default_on_error)
}

// 3.c Second level wrapper

async function legacyOnOff(ip_addr, new_State) {
    legacy({
        msgType: "switch",
        state: new_State,
        address: ip_addr
    })
}

async function dim(ip_addr, val){
    setLcmDim(ip_addr, {level: val})
}

async function lampregistration(ip_addr, hub_id, lamp_serial_number, latitude, longitude){
    addLamp(ip_addr, {
        hubid: hub_id,
        key: lamp_serial_number,
        latitude: latitude,
        longitude: longitude
    });
}

// 3.d Group related API

async function getGroups() {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    return await getRequest(authT, _endpoints.rootGroup, function () {
        console.log("Get Groups request Successful")
    }, default_on_error);
}

async function getGroup(name) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.groupName.replace("{name}", name);
    return await getRequest(authT, url, function () {
        console.log("Get Group request Successful");
    }, default_on_error);
}

async function addGroup(body, ifSuccess, ifFail) {
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = _endpoints.rootGroup;
    await postRequest(authT, url, body, function () {
        displayUpdate("console", "Group Created")
        ifSuccess();
    }, function (jqXHR, textStatus, errorThrown) {
        console.error('Error creatign group: ', textStatus, ', Details: ',
            errorThrown);
        console.error('Response: ', jqXHR.responseText);
        ifFail();
    });
}

async function setGroupDim(groupname, body){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.groupDim.replace("{name}", groupname);
    return await putRequest(authT, url, body, function () {
        displayUpdate("console", "Group dim level has been set to " + body.level);
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming group: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
    });
}

async function group_dim(name, val){
    setGroupDim(name, {level: val})
}

async function group_name_put(groupname, requestBody, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.groupName.replace("{name}", groupname);
    return await putRequest(authT, url, requestBody, function () {
        displayUpdate("console", "Successfuly updated the changes");
        onSuccess();
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming group: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure();
    });
}

async function group_profile_change(groupName, requestBody, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.groupProfile.replace("{name}", groupName);
    return await putRequest(authT, url, requestBody, function () {
        displayUpdate("console", "Successfuly updated the changes");
        onSuccess();
    },function (jqXHR, textStatus, errorThrown) {
        console.error('Error dimming group: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure();
    });
}

async function lcm_otau(ipv6, requestBody, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.lcmOTAU.replace("{lcmid}", ipv6);
    return await putRequest(authT, url, requestBody, function () {
        displayUpdate("console", "Successfuly initiated lcm OTA update");
        onSuccess();
    },function (jqXHR, textStatus, errorThrown) {
        displayUpdate("console", "Failed to initiate lcm OTA update");
        console.error('Error dimming group: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure();
    });
}

async function group_otau(name, requestBody, onSuccess, onFailure){
    let authT;
    await idt_ice.authToken.then(function (data) {
        authT = data;
    });
    url = await _endpoints.groupOTAU.replace("{name}", name);
    return await putRequest(authT, url, requestBody, function () {
        displayUpdate("console", "Successfuly initiated group OTA update");
        onSuccess();
    },function (jqXHR, textStatus, errorThrown) {
        displayUpdate("console", "Failed to initiate group OTA update");
        console.error('Error dimming group: ', textStatus);
        console.error('Details: ', errorThrown);
        console.error('Response: ', jqXHR.responseText);
        onFailure();
    });
}