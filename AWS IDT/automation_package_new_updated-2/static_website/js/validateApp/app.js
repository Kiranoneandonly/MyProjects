function sketchQR(val, width, height, colorDark, colorLight, id) {
    new QRCode(document.getElementById(id), {
        text: val,
        width: width,
        height: height,
        colorDark: colorDark,
        colorLight: colorLight,
        correctLevel: QRCode.CorrectLevel.H
    });
}

async function prepValidateAppPage(){
    await $("#ice-content").replaceWith(validateAppUI.canvas());
    sketchQR(_config.api.invokeUrl, 200, 200, "#06357a", "#ffffff", "qrcode");
}

async function prepScanAppCanvas() {
    prepValidateAppPage();  
}