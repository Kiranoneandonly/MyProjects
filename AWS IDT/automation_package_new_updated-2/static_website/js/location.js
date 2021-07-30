let map;
//create content dictionary
let contentDictionary = {};
let latitudeSum = 0;
let longitudeSum = 0;
let latitudeCount = 0;
let longitudeCount = 0;
let latitudeArray = [];
let longitudeArray = [];
let middleLat = 0;
let middleLong = 0;
let iconsBase = 'https://maps.google.com/mapfiles/kml/paddle/';
let hubDataObject = {};
let latLngObject = {};
let address = "";
//Adding Coordinates Dictionary
let coordObject = {};
let totalDict = {};
async function getCoordinates() {
    let authT;
    await idt_ice.authToken.then(function(data){authT = data});
    await $.ajax({
        url: _config.api.invokeUrl + "/idt/lcm",
        beforeSend: function(request) {
            request.setRequestHeader('authToken',authT);
        },
        contentType: "application/json",
        dataType: 'json',
        success: async function(result){
            await uponSuccess(result)
            await $(document).foundation();
        },
        error: function ajaxError(jqXHR, textStatus, errorThrown) {
            console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
            console.error('Response: ', jqXHR.responseText);
        }
    });
}

function uponSuccess(result) {
    for (let i = 0; i < result.length; i++) {
        let latitude = result[i]['latitude'];
        let longitude = result[i]['longitude'];
        let hubID = result[i]['hubid'];
        let status = result[i]['status'];
        let ip = result[i]['ip'];
        let slicedIP = ip.slice(17, ip.length);
        //Add to Hub Data Object
        hubDataObject[i] = {
            "latitude": latitude,
            "longitude": longitude,
            "hubID": hubID,
            "status": status,
            "ipAddress": ip,
            "ipAbbreviation": slicedIP,
        }
        contentDictionary[i] = '<div id="content">' +
            '<div id="siteNotice">' +
            '</div>' +
            '<h5 id="firstHeading" class="firstHeading">' + hubID + '</h5>' +
            '<div id="bodyContent">' +
            '<h6><b>Status</b>: ' + status + '</h6>' +
            '<h6><b>Hub ID</b>: ' + hubID + '</h6>' +
            '<h6><b>Latitude</b>: ' + latitude + '</h6>' +
            '<h6><b>Longitude</b>: ' + longitude + '</h6>' +
            '<h6><b>IP Address</b>: ' + ip + '</h6>' +
            '</div>' +
            '</div>';
        totalDict[i] = {
            "latitude": latitude,
            "longitude": longitude,
            "hubID": hubID,
            "status": status,
            "ipAddress": ip,
            "ipAbbreviation": slicedIP,
            "content": contentDictionary[i],
        }
        if (latitude && longitude) {
            latLngObject[i] = { "latitude": latitude, "longitude": longitude };
            latitudeSum += latitude;
            longitudeSum += longitude;
            latitudeArray.push(latitude);
            longitudeArray.push(longitude);
            latitudeCount++;
            longitudeCount++;
        }
    }
    //End of For Loop
    latitudeArray = latitudeArray.sort();
    longitudeArray = longitudeArray.sort();
    //Adding Coord Object
    for (let i = 0; i < latitudeArray.length; i++) {
        for (let j = 0; j < longitudeArray.length; j++) {
            coordObject[i] = {
                "latitude": latitudeArray[i],
                "longitude": longitudeArray[j]
            }
        }
    }
    middleLat = latitudeArray[Math.round((latitudeArray.length - 1) / 2)];
    middleLong = longitudeArray[Math.round((latitudeArray.length - 1) / 2)];


    //Initializing Google Maps
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 12,
        center: new google.maps.LatLng(middleLat, middleLong),
        mapTypeId: 'hybrid'
    });

    for (const [key, value] of Object.entries(totalDict)){
        if(value["latitude"] && value["longitude"]){
            if(value['status'] == 'online'){
                let marker = new google.maps.Marker({
                    position: { lat: value["latitude"], lng: value["longitude"] },
                    map: map,
                    mapTypeId: 'hybrid',
                    title: value["hubID"],
                    icon: iconsBase + 'grn-blank.png'
                });
                marker.addListener('click', function () {
                    infowindow.open(map, marker);
                });
                let infowindow = new google.maps.InfoWindow({
                    content: value["content"]
                });
            }
            else if (value['status'] == "commissioning started" || value["status"] == "commisioning started") {
                let marker = new google.maps.Marker({
                    position: { lat: value["latitude"], lng: value["longitude"] },
                    map: map,
                    mapTypeId: 'hybrid',
                    title: value["hubID"],
                    icon: iconsBase + 'ylw-blank.png'
                });
                marker.addListener('click', function () {
                    infowindow.open(map, marker);
                });
                let infowindow = new google.maps.InfoWindow({
                    content: value["content"]
                });
            }
            else {
                let marker = new google.maps.Marker({
                    position: { lat: value["latitude"], lng: value["longitude"] },
                    map: map,
                    mapTypeId: 'hybrid',
                    title: value["hubID"],
                    icon: iconsBase + 'red-square.png'
                });
                marker.addListener('click', function () {
                    infowindow.open(map, marker);
                });
                let infowindow = new google.maps.InfoWindow({
                    content: value["content"]
                });
            }
        }
        else{
            continue;
        }
    }
}