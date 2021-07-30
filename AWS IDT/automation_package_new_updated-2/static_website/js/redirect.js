async function route(page) {
    await $('.reveal-overlay').remove();
    await onSpinner();
    switch (page) {
        // Pre Signin Pages
        case "changeForgotPassword":
            prepChangeForgotPasswordCanvas();
            offSpinner();
            break;
        case "changePassword":
            prepChangePasswordCanvas();
            offSpinner();
            break;
        case "forgotPassword":
            prepForgotPasswordCanvas();
            offSpinner();
            break;
        case "register":
            prepRegisterCanvas();
            offSpinner();
            break;
        case "signin":
            signout();
            offSpinner();
            break;
        case "verify":
            prepVerifyCanvas();
            offSpinner();
            break;
        
        // Post-Signin Pages
        case "lcmdim":
            require(['lcms/canvas', 'lcms/app'],
                function (lcmsCanvas, lcmsApp) {
                    loadLcmDim();
                });
            break;
        case "lcmMonitor":
            require(['monitorLcm/google-config', 'monitorLcm/canvas','monitorLcm/app','monitorLcm/location'],
                function (gconf, monitorCanvas, lcmMonitorApp, location) {
                    loadLcmMonitor();
                });
            break;
        case "registerlcm":
            require(['registerLcm/canvas', 'registerLcm/app'],
                function (registerLcmCanvas, lcmRegistration) {
                    loadregisterLcm();
                });
            break;
        case "validateApp":
            require(['qrcode'],
                function (qrcode) {
                    requirejs(['validateApp/canvas', 'validateApp/app'],
                        function (validateAppCanvas, validateAppApp) {
                            loadValidateApp();
                        });
                });
            break;
        case "schedular":
            require(["schedular/canvas","schedular/app"],
                function (SchedularCanvas, SchedularApp) {
                    loadSchedular();
                });
            break;
        case "group":
            require(['groups/canvas',"groups/app"], 
            function(groupsCanvas, groupsApp){
                loadGroups();
            });
            break;
        case "addGroup":
            require(['addGroup/canvas',"addGroup/app"], 
                function(groupsCanvas, groupsApp){
                    loadAddGroup();
            });
            break;
        case "loadLcm":
            require(['loadLcm/canvas',"loadLcm/app"], 
                function(loadLcmCanvas, loadLcmApp){
                    loadLcmLoader();
            });
            break;
        default:
            require(['groups/canvas',"groups/app"], 
            function(groupsCanvas, groupsApp){
                loadGroups();
            });
            break;
    }
}

async function loadLcmDim() {
    await prepLcmDim();
    setPageCookie('lcmdim');
    offSpinner();
}

async function loadregisterLcm() {
    await prepRegisterLCMCanvas();
    setPageCookie('registerlcm');
    offSpinner();
}

async function loadValidateApp() {
    await prepScanAppCanvas();
    setPageCookie('validateApp');
    offSpinner();
}

async function loadLcmMonitor(){
    await prepLampsMonitorCanvas();
    setPageCookie('lcmMonitor');
    offSpinner();
}

async function loadSchedular(){
    await prepSchedularCanvas();
    setPageCookie("schedular");
    offSpinner();
}

async function loadGroups(){
    await groupApp.start();
    setPageCookie("group");
    offSpinner();
}

async function loadAddGroup(){
    await addGroupApp.start();
    setPageCookie("addGroup");
    offSpinner();
}

async function loadLcmLoader(){
    await loadLcmApp.start();
    setPageCookie("loadLcm");
    offSpinner();
}

async function setPageCookie(page){
    Cookies.set('ice_page', page, {
        expires: 7
    });
}