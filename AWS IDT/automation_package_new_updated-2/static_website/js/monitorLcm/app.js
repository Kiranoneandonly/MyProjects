async function prepLampsMonitorCanvas() {
    let mapsUrl = await googleMapsConfig.baseUrl+googleMapsConfig.endpoint+googleMapsConfig.query
    mapsUrl = await mapsUrl.replace("{apikey}",googleMapsConfig.apikey)
    console.log(mapsUrl)
    await $("#ice-content").replaceWith(monitorLCMUI.canvas(mapsUrl));
    await $("#ice-content").foundation();
  }