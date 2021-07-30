window._endpoints = {
    // -----------------------  Hub  -------------------------------
    rootHub: _config.api.invokeUrl+"/idt/hub",
    hub: _config.api.invokeUrl+"/idt/hub/{hubid}",
    hubUpdate: _config.api.invokeUrl+"/idt/hub/{hubid}/update",
    hubUpdateGateway: _config.api.invokeUrl+"/idt/hub/{hubid}/update/gateway",
    hubUpdateLcm: _config.api.invokeUrl+"/idt/hub/{hubid}/update/lcm",

    // -----------------------  Lcm  ------------------------------- 
    rootLcm: _config.api.invokeUrl+"/idt/lcm",
    lcmLoad: _config.api.invokeUrl+"/idt/lcm/load",
    lcm: _config.api.invokeUrl+"/idt/lcm/{lcmid}",
    lcmDim: _config.api.invokeUrl+"/idt/lcm/{lcmid}/dim",
    lcmUpdate: _config.api.invokeUrl+"/idt/lcm/{lcmid}/update",
    lcmDimrgb: _config.api.invokeUrl+"/idt/lcm/{lcmid}/dim-rgb",
    lcmOTAU: _config.api.invokeUrl+"/idt/lcm/{lcmid}/otau",

    // -----------------------  Legacy  -------------------------------
    legacyOnOff: _config.api.invokeUrl+"/idt/ulamp",

    // -----------------------  Scedular  -------------------------------
    schedularDay: _config.api.invokeUrl+"/schedular/day",
    schedularWeek: _config.api.invokeUrl+"/schedular/week",

    // -----------------------  Group  -------------------------------
    rootGroup: _config.api.invokeUrl+"/idt/group",
    groupName: _config.api.invokeUrl+"/idt/group/{name}",
    groupDim: _config.api.invokeUrl+"/idt/group/{name}/dim",
    groupProfile: _config.api.invokeUrl+"/idt/group/{name}/profile",
    groupOTAU: _config.api.invokeUrl+"/idt/group/{name}/otau"

}