let _paging;
let _pagingSetting={
  sizes: [12,24,36,48,60]
}
let searchCache={
  lcmList: null,
  query: null,
  type: "commissioned"
}

function showLampCanvasContent() {
  $("#ice-content").replaceWith(lcmUI.canvas());
}

async function showlampCard(lamp) {
  await $("#lamp-card-container").append(lcmUI.lcmCard(lamp));
  // await $(`#lamp-cell-${lamp.key}`).foundation();
}

async function showLampModel(lamp) {
  await $(`#model-${lamp.key}`).replaceWith(lcmUI.lcmModel(lamp));
  $(`#model-${lamp.key}`).foundation();
}

function showLampCanvasSubMenu(){
  $('#sub-bar').replaceWith(lcmUI.subMenu());
  populatePageSize();
  $('#sub-bar').foundation();
}

function showLcmCardContainer(){
  $("#card-container").replaceWith(lcmUI.lcmCardContainer())
}

async function preplcmmod(id){
  var lampsDetails = await getLampList();
  let searched = await searchLamps([["lcmid","equals",id]],lampsDetails);
  await showLampModel(searched[0])
}

async function lazyModelPrep(id){
  if($(`#model-${id}`).children().length>0){
  }else{
    await preplcmmod(id);
  }
}

function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

async function searchLamps(query, lcms){
  if(_debug){
    console.log("searchLamps: query: ", query);
    console.log("searchLamps: lcms length: ", lcms.length);
  }
  let result = [];
  lcms.forEach(async (element)=>{
    if(checkCriteria(query,element)){
      result.push(element);
    }
  });
  if(_debug){
    console.log("searchLamps: result: ", result.length);
  }
  if(_debug){
    console.log("searchLamps: result: ", result);
  }
  return result;
}

function checkCriteria(query, element){
  if(_debug){
    console.log("checkCriteria: prop[1]: ", query);
  }
  let res = false;
  query.forEach(function (prop){
    switch(prop[0]){
      case "lcmid":
          res =  checkCondition(prop[1],prop[2],element.key);
        break;
      case "hubid":
        res =  checkCondition(prop[1],prop[2], element.hubid);
        break;
      case "lcmip":
        res = checkCondition(prop[1],prop[2], element.ip);
        break;
    }
  });
  return res;
}

function checkCondition(condition, val, str){
  if(_debug){
    console.log("checkCondition: condition: ", condition);
    console.log("checkCondition: val: ", val);
    console.log("checkCondition: str: ", str);
  }
  if(condition=="equals"){
    let res = val.toUpperCase() === str.toUpperCase();
    if(res==false){
      return false;
    }
    return true;
  }else if(condition=="contains"){
    let res = str.toUpperCase().includes(val.toUpperCase());
    if(res==false){
      return false;
    }
    if(_debug){
      console.log(res,"  ", val)
    }
    return true;
  }
  return true;
}

async function displaySearchResult(query, type){
  if(_debug){
    console.log("query: ",query);
    console.log("type: ", type);
  }
  let result = [];
  let lcms = [];
  if(type==null){
    lcms = await getLampList();
  }else{
    lcms = await getfilteredResult(type);
  }
  if(query==null){
    result = lcms;
  }else{
   result = await searchLamps(query, lcms);
  }
  await prepLcmDimPage(result, false);
}

async function filterDecommissioned(elements){
  let commissioned = []
  let decommissioned = []
  await elements.forEach(async (element)=> {
  if (element.status != "decommissioned" && element.status != "Decommissioned") {
    commissioned.push(element)
  }else{
    decommissioned.push(element)
  }
  });
  return [commissioned,decommissioned];
}

async function getfilteredResult(type){
  let filtered=null;
  if(type==null || type=="both"){
    return getLampList();
  }
  if(filtered==null){
    filtered = await filterDecommissioned(await getLampList());
  }
  if(type=="commissioned"){
    return filtered[0];
  }
  if(type=="decommissioned"){
    return filtered[1];
  }
  return getLampList();
}

async function prepLcmDim(){
  await $('.reveal-overlay').remove();
  await showLampCanvasContent();
  await showLampCanvasSubMenu();
  await showLcmCardContainer();
  await displaySearchResult(null,"commissioned");
  setlastSearch(null,"commissioned");
}

async function prepLcmDimPage(lampsDetails, showDecommissioned){
  let page = await getPagingInfo();
  let counterlimit=0;
  if(_debug){
    console.log("number of lcm: ",lampsDetails.length);
    console.log("page limit:", page['page_size']*page['page_num']+page['page_size'])
  }
  if(lampsDetails.length<page['page_size']*page['page_num']+page['page_size']){
    counterlimit = lampsDetails.length;
  }else{
    counterlimit = page['page_size'] + page['page_size']*page['page_num'];
  }
  for(let i=page['page_size']*page['page_num']; i<counterlimit; i++){
    showlampCard(lampsDetails[i]);
  }
  $("#lamp-card-container").foundation();
  let pages = lampsDetails.length/page['page_size'];
  populatePageNumber(pages);
}

function getPagingInfo(){
  if(_paging==null){
    _paging = {};
    _paging['page_size']=24;
    _paging['page_num']=0;
  }
  return _paging;
}

function setPageSize(size){
  if(_paging==null){
    _paging = {};
    _paging['page_num']=0;
  }
  _paging['page_size']=size;
}

function setPageNum(num){
  if(_paging==null){
    _paging = {};
    _paging['page_size']=24;
  }
  _paging['page_num']=num;
}

function selectPageSize(){
  let e = document.getElementById("paging");
  let page_size = e.options[e.selectedIndex].value;
  setPageSize(parseInt(page_size));
  setPageNum(0);
  $('.reveal-overlay').remove();
  showLcmCardContainer();
  let search = lastSearch();
  displaySearchResult(search.query,search.type);
}

function populatePageSize(){
  _pagingSetting.sizes.forEach(function(size){
    if(size==getPagingInfo()['page_size']){
      $("#paging").append(lcmUI.selectorOption(size,size,"selected"));
    }else{
      $("#paging").append(lcmUI.selectorOption(size,size,""));
    }
  });
  $("#paging").foundation()
}

function populatePageNumber(pages){
  $("#pagination").find('option').remove()
  for(let i=0; i<pages; i++){
    if(i==getPagingInfo()['page_num']){
      $("#pagination").append(lcmUI.selectorOption(i,i+1,"selected"));
    }else{
      $("#pagination").append(lcmUI.selectorOption(i,i+1,""));
    }
  }
}

function selectPage(){
  let e = document.getElementById("pagination");
  let num =  e.options[e.selectedIndex].value;
  setPageNum(parseInt(num));
  showLcmCardContainer();
  let search = lastSearch();
  displaySearchResult(search.query,search.type);
}

function lastSearch(){
  if(_debug){
    console.log(searchCache);
  }
  return searchCache;
}

function setlastSearch(query, type){
  if(_debug){
    console.log(query, type);
  }
  searchCache.query = query;
  searchCache.type = type;
}

function searchLcm(){
  let e = document.getElementById("search-select");
  let type =  e.options[e.selectedIndex].value;
  let val = document.getElementById("search-text").value;
  let query = [[type,"contains",val]]
  if(_debug){
    console.log("search initiated with query: ",query);
  }
  setPageNum(0);
  $('.reveal-overlay').remove();
  showLcmCardContainer();
  displaySearchResult(query,"commissioned");
  setlastSearch(query, "commissioned");
}

async function decommissionlcm(key,ipv6Addr) {
  let authT;
  let error = false;
  await $(".form-error").hide();
  await idt_ice.authToken.then(function (data) {
    authT = data
  });

  let confirm = await document.getElementById(`decommission-${key}`).value;
  if (confirm == "" || confirm != key) {
    $(`decommission-error-${key}`).show();
    error = true;
  }
  console.log(ipv6Addr)
  if (!error) {
    deleteLamp(ipv6Addr, function () {
      console.log("lcm decommissioned")
      $(`#decommission-callout-success-${key}`).show();
  }, function (jqXHR, textStatus, errorThrown) {
      console.error('Error toggling address: ', textStatus, ', Details: ',
          errorThrown);
      console.error('Response: ', jqXHR.responseText);
      $(`#decommission-callout-fail-${key}`).show();
  })
  } else {
    $(`#decommission-callout-fail-${key}`).show();
  }
}

lcmApp = {
  rgbToHex: function(rgb){
    if (typeof rgb === "undefined"){
      return "#000000"
    }
    let componentToHex = function(c) {
      var hex = c.toString(16);
      return hex.length == 1 ? "0" + hex : hex;
    }
    
    return "#"+componentToHex(rgb.red)+componentToHex(rgb.green)+componentToHex(rgb.blue);
  },

  hextoRGB: function (hex){
    let result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      red: parseInt(result[1], 16),
      green: parseInt(result[2], 16),
      blue: parseInt(result[3], 16)
    } : null;
  },

  setColor: function(ip, key){
    let hex = document.getElementById(`rgb-card-${key}`).value;
    let rgb = lcmApp.hextoRGB(hex);
    if(rgb===null){
      displayUpdate("console",`LCM ${key} failed set rgb value ${hex}`);
      return;
    }
    let onSuccess = function(){
      displayUpdate("console",`LCM ${key} rgb value set to ${hex}`);
    }
    let onFailure = function() {
      displayUpdate("console",`LCM ${key} failed set rgb value ${hex}`);
    }
    setLcmDimRGB(ip, rgb, onSuccess, onFailure)
  },

  otau: function(ipv6, key){
    let otalink = document.getElementById(`otau-${key}`).value;
    if(otalink==""){
      return;
    }
    displayUpdate("console",`ipv6: ${ipv6} key: ${key}`);
    lcm_otau(ipv6, {"firmware-file": otalink}, function(){
      lcmApp.showCalloutForMS(".lcm-ota-success",10000);
    }, function(){
      lcmApp.showCalloutForMS(".lcm-ota-fail",10000);
    });
  },

  showCalloutForMS: async function(callout,ms){
    await $(callout).show();
    await groupApp.sleep(ms);
    $(`${callout} .close-button`).trigger('close');
  },

}

$(document).on('keypress',function(e) {
  if(e.which == 13) {
    if(e.target == document.getElementById("search-text")){
      searchLcm();
    }
  }
});