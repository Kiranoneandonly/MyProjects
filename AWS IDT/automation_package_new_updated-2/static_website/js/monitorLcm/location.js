let map,poly,contentDictionary = {};
let latitudeSum = 0,longitudeSum = 0,latitudeCount = 0,longitudeCount = 0,
latitudeArray = [],longitudeArray = [],coordsArray = [],middleLat = 0,middleLong = 0;
let iconsBase = "http://maps.google.com/mapfiles/kml/paddle/";
let hubDataObject = {},latLngObject = {},address = "",coordObject = {},
totalDict = {},polylineLatlngObject = {},newObject = {},ipCoordsObject = {};
let uplinkValue, ipAddress, totalLatitude, totalLongitude, polylineObject;
let ipLinkArray = [], ipLatLngObject = ({}.ipCoordsObject = {}),newLinkArray = [];
let rssi, uplink, coords, ipKey, coordsKey;
let firstLink,secondLink,linkUplnk,firstLinkLat,firstLinkLng,secondLinkLat, secondLinkLng;
let firstIP,secondIP,firstLat,firstLng,uplinkLat,uplinkLng,polyRSSI, polylineCoordsArray = [];
let linkLat, linkLng, flightPath, signalStrength, mySignalStrength;

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
            //Add new function here for polylines
            await getPolylines(result)
            await drawPolylines(result)
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
        if (result[i]["rssi"]) {
            let rssi = result[i]["rssi"];
          } else {
            continue;
          }
          if (result[i]["uplink"]) {
            let uplink = result[i]["uplink"];
          } else {
            continue;
          }
        //Adding Coordinates Array
        coordsArray.push([latitude, longitude]);
        let hubID = result[i]['hubid'];
        let status = result[i]['status'];
        let ip = result[i]['ip'];
        let slicedIP = ip.slice(17, ip.length);
        let latLng = coordsArray;
        let rssi = result[i]["rssi"];
        let uplink = result[i]["uplink"];
        //Add to Hub Data Object

        hubDataObject["ipAddress"] = {
            latitude: latitude,
            longitude: longitude,
            hubID: hubID,
            status: status,
            ipAddress: ip,
            ipAbbreviation: slicedIP,
            coordinatesArray: latLng,
            rssi: rssi,
            uplink: uplink
          };

          contentDictionary[i] =
            '<div id="content">' +
            '<div id="siteNotice">' +
            "</div>" +
            '<h5 id="firstHeading" class="firstHeading">' +
            hubID +
            "</h5>" +
            '<div id="bodyContent">' +
            "<h6><b>Status</b>: " +
            status +
            "</h6>" +
            "<h6><b>Hub ID</b>: " +
            hubID +
            "</h6>" +
            "<h6><b>Latitude</b>: " +
            latitude +
            "</h6>" +
            "<h6><b>Longitude</b>: " +
            longitude +
            "</h6>" +
            "<h6><b>IP Address</b>: " +
            ip +
            "</h6>" +
            "<h6><b>RSSI</b>: " +
            rssi +
            "</h6>" +
            "<h6><b>Uplink</b>: " +
            uplink +
            "</h6>" +
            "</div>" +
            "</div>";
          totalDict[i] = {
            latitude: latitude,
            longitude: longitude,
            hubID: hubID,
            status: status,
            ipAddress: ip,
            ipAbbreviation: slicedIP,
            rssi: rssi,
            uplink: uplink,
            content: contentDictionary[i],
            coordinatesArray: coordsArray
          };

        if (latitude && longitude) {
            latLngObject[i] = { lat: Number(latitude), lng: Number(longitude) };
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
            if (value["status"] == "online") {
              uplinkValue = value["uplink"];
              ipAddress = value["ipAddress"];
              totalLatitude = value["latitude"];
              totalLongitude = value["longitude"];
              rssiValue = value["rssi"];
              newObject[ipAddress] = {
                rssi: rssiValue,
                uplink: uplinkValue,
                coords: { lat: totalLatitude, lng: totalLongitude }
              };
              ipCoordsObject[ipAddress] = {
                lat: Number(totalLatitude),
                lng: Number(totalLongitude)
              };
              let marker = new google.maps.Marker({
                position: {
                  lat: value["latitude"],
                  lng: value["longitude"]
                },
                map: map,
                mapTypeId: "hybrid",
                title: value["hubID"],
                icon: iconsBase + "grn-blank.png"
              });
              marker.addListener("click", function() {
                infowindow.open(map, marker);
              });
              let infowindow = new google.maps.InfoWindow({
                content: value["content"]
              });
            } else if (
              value["status"] == "commissioning started" ||
              value["status"] == "commisioning started"
            ) {
                uplinkValue = value["uplink"];
                ipAddress = value["ipAddress"];
                totalLatitude = value["latitude"];
                totalLongitude = value["longitude"];
                rssiValue = value["rssi"];
                newObject[ipAddress] = {
                  rssi: rssiValue,
                  uplink: uplinkValue,
                  coords: {
                    lat: totalLatitude,
                    lng: totalLongitude
                  }
                };
                ipCoordsObject[ipAddress] = {
                  lat: Number(totalLatitude),
                  lng: Number(totalLongitude)
                };
              let marker = new google.maps.Marker({
                position: {
                  lat: value["latitude"],
                  lng: value["longitude"]
                },
                map: map,
                mapTypeId: "hybrid",
                title: value["hubID"],
                icon: iconsBase + "ylw-blank.png"
              });
              marker.addListener("click", function() {
                infowindow.open(map, marker);
              });
              let infowindow = new google.maps.InfoWindow({
                content: value["content"]
              });
            } else {
                uplinkValue = value["uplink"];
                ipAddress = value["ipAddress"];
                totalLatitude = value["latitude"];
                totalLongitude = value["longitude"];
                rssiValue = value["rssi"];
                newObject[ipAddress] = {
                  rssi: rssiValue,
                  uplink: uplinkValue,
                  coords: {
                    lat: totalLatitude,
                    lng: totalLongitude
                  }
                };
                ipCoordsObject[ipAddress] = {
                  lat: Number(totalLatitude),
                  lng: Number(totalLongitude)
                };
              let marker = new google.maps.Marker({
                position: {
                  lat: value["latitude"],
                  lng: value["longitude"]
                },
                map: map,
                mapTypeId: "hybrid",
                title: value["hubID"],
                icon: iconsBase + "red-square.png"
              });
              marker.addListener("click", function() {
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

//End of Upon Success - Time to add new method

function getPolylines(result) {
  for (const [key, value] of Object.entries(newObject)) {
    let myRSSI = value["rssi"];
    if (myRSSI > -100 && myRSSI < -70) {
      mySignalStrength = "low";
    } else if (myRSSI > -70 && myRSSI <= -35) {
      mySignalStrength = "medium";
    } else if (myRSSI > -35 && myRSSI < 0) {
      mySignalStrength = "high";
    }
    let count = 0;
    polylineCoordsArray.push({
      lat: newObject[key]["coords"]["lat"],
      lng: newObject[key]["coords"]["lng"],
      rssi: myRSSI,
      signalStrength: mySignalStrength
    });
    polyRSSI = newObject[key]["rssi"];

  }
}

function drawPolylines(result){
    for (let i = 0; i < polylineCoordsArray.length; i += 2) {
        if (polylineCoordsArray[i]["signalStrength"] == "high") {
          flightPath = new google.maps.Polyline({
            path: [polylineCoordsArray[i], polylineCoordsArray[i + 1]],
            geodesic: true,
            strokeColor: "#00FF00",
            strokeOpacity: 1.0,
            strokeWeight: 2
          });
          flightPath.setMap(map);
          //Added Geocoding Functionality
          // geocoder = new google.maps.Geocoder;
          // let reverseGeocodeAddress = geocodeLatLng(geocoder, polylineCoordsArray[i], polylineCoordsArray[i+1]);
          // console.log(reverseGeocodeAddress);
        }
        else if (polylineCoordsArray[i]["signalStrength"] == "medium") {
          flightPath = new google.maps.Polyline({
            path: [polylineCoordsArray[i], polylineCoordsArray[i + 1]],
            geodesic: true,
            strokeColor: "#FFFF00",
            strokeOpacity: 1.0,
            strokeWeight: 2
          });
          flightPath.setMap(map);
          // geocoder = new google.maps.Geocoder;
          // let reverseGeocodeAddress = geocodeLatLng(geocoder, polylineCoordsArray[i], polylineCoordsArray[i+1]);
          // console.log(reverseGeocodeAddress);
        }
        else if (polylineCoordsArray[i]["signalStrength"] == "low") {
          flightPath = new google.maps.Polyline({
            path: [polylineCoordsArray[i], polylineCoordsArray[i + 1]],
            geodesic: true,
            strokeColor: "#FF0000",
            strokeOpacity: 1.0,
            strokeWeight: 2
          });
          flightPath.setMap(map);
          // geocoder = new google.maps.Geocoder;
          // let reverseGeocodeAddress = geocodeLatLng(geocoder, polylineCoordsArray[i], polylineCoordsArray[i+1]);
          // console.log(reverseGeocodeAddress);
        }
        else{
          console.log("None of the above!");
        }
      }
}