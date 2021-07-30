async function validateLampRegisterForm(ipv6Addr, lampSerialNumber, hubID, longitude, latitude) {
    let error;
    resetLampRegisterFormErrorDisplay();

    if (longitude == "" || longitude == NaN) {
        $("#longitudeError1").show();
        error = true;
    }
    if (latitude == "" || latitude == NaN) {
        $("#latitudeError1").show();
        error = true;
    }
    if (hubID == "" || hubID == null) {
        $("#hubIDError1").show();
        error = true;
    }
    if (ipv6Addr == "" || ipv6Addr == null) {
        $("#luminaire-ipError1").show();
        error = true;
    }
    if (lampSerialNumber == "" || lampSerialNumber == null) {
        $("#luminaireError1").show();
        error = true;
    }
    return await error;
}

async function validatenandRegisterLamp() {
    let longitude = await document.getElementById("longitude").value;
    let latitude = await document.getElementById("latitude").value;
    let hubID = await document.getElementById("hubID").value;
    let ipv6Addr = await document.getElementById("luminaire-ip").value;
    let lampSerialNumber = await document.getElementById("luminaire").value;
    let error = await validateLampRegisterForm(ipv6Addr, lampSerialNumber, hubID, longitude, latitude)
    if (!error) {
        lampregistration(ipv6Addr, hubID, lampSerialNumber, latitude, longitude)
    } else {
        $(".form-error-callout").show();
    }
}

async function registerLamp() {
    validatenandRegisterLamp()
}

async function prepRegisterLCMCanvas() {
    await $("#ice-content").replaceWith(registerlcmUI.canvas());
    await loadQRReader();
    await fillVideoSourceInDropDown();
    await $("#ice-content").foundation();
}

let codeReader;
let videoInputs;
let selectedDeviceId;
async function loadQRReader() {
    codeReader = await new ZXing.BrowserQRCodeReader();
    await console.log('ZXing code reader initialized');
    await codeReader.getVideoInputDevices().then((videoInputDevices) => {
        videoInputs = videoInputDevices;
        selectedDeviceId = videoInputDevices[0].deviceId;
    }).catch((err) => {
        console.error(err)
    });
}

function startQRScanner() {
    console.log(selectedDeviceId);
    $(".responsive-embed").show();
    codeReader.decodeFromInputVideoDevice(selectedDeviceId, 'video')
        .then((result) => {
            console.log(result)
            let values = result.text.split(" ");
            $('#luminaire').val(values[1]);
            $('#luminaire-ip').val(values[0]);
            codeReader.reset();
            $(".responsive-embed").hide();
            $("#luminaireError1").hide();
            $("#luminaire-ipError1").hide();
        }).catch((err) => {
            console.error(err)
            $("fi-alert").text(err);
            $("form-error-callout").css("display: block");
        });
    console.log("Started continous decode from camera with id", selectedDeviceId);
}

function resetQRScanner() {
    codeReader.reset();
    $(".responsive-embed").hide();
    console.log('Reset.');
}

async function fillVideoSourceInDropDown() {
    const sourceSelect = await document.getElementById('sourceSelect');
    if (videoInputs.length >= 1) {
        videoInputs.forEach((element,index) => {
            const sourceOption = document.createElement('option')
            sourceOption.text = element.label
            sourceOption.value = index;
            sourceSelect.appendChild(sourceOption)
        });

        sourceSelect.onchange = () => {
            selectedDeviceId = videoInputs[sourceSelect.value].deviceId;

        }
    }
}

function resetLampRegisterFormErrorDisplay() {
    $(".callout").hide();
    $(".form-error").hide();
}

function resetRegisterLampForm() {
    $(".form-error").attr("class", ".form-error");
    $(".is-invalid-label").attr("class", "");
    $(".is-invalid-input").attr("class", "");
    $(".callout").hide();
    $(".form-error").hide();
    $("input").val("");
}

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(showPosition);
    } else {
        $("fi-alert").text("Geolocation is not supported by this browser.");
        $("form-error-callout").css("display: block");
    }
}


function showPosition(position) {
    document.getElementById("longitude").value = position.coords.longitude;
    document.getElementById("latitude").value = position.coords.latitude;
}