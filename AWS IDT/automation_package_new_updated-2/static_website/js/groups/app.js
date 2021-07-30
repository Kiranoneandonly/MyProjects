let groupApp = {
  diplayIceContent: function () {
    $("#ice-content").replaceWith(groupUI.canvas());
  },

  displaySubMenu: function () {
    $('#sub-bar').replaceWith(groupUI.subMenu());
    groupApp.populateGroupPageSize();
    $('#sub-bar').foundation();
  },

  displayCardContainer: function () {
    $("#card-container").replaceWith(groupUI.groupCardContainer())
  },

  displayGroupCard: async function (group) {
    await $("#group-card-container").append(groupUI.groupCard(group));
  },

  displayGoupModal: async function(group){
    await $(`#model-${group.name}`).replaceWith(groupUI.groupModal(group));
    await $(`#model-${group.name}`).foundation();
  },

  start: function () {
    groups = getGroupList();
    groupApp.diplayIceContent();
    groupApp.displaySubMenu();
    groupApp.displayCardContainer();
    groups.then(function (grps) {
      groupApp.paginate(grps['group'],groupApp.displayGroupCard)
    });
  },

  populateGroupPageSize: function () {
    pageSetting = groupApp.getPageSetting();
    displayUpdate("console", pageSetting);
    groupApp.paginationSetting.sizes.forEach(function (size) {
      if (size == pageSetting['page_size']) {
        $("#paging").append(groupUI.selectorOption(size, size, "selected"));
      } else {
        $("#paging").append(groupUI.selectorOption(size, size, ""));
      }
    });
    $("#paging").foundation()
  },

  paginationSetting: {
    sizes: [12, 24, 36, 48, 60],
    pageSetting: null,
    query: null,
    defaultPageSize: 24
  },

  prepGroupModal: async function(name){
    result = await groupApp.search([["name", "equals", name]]);
    await groupApp.displayGoupModal(result[0]);
  },

  lazyModelPrep: async function (name){
    if($(`#model-${name}`).children().length>0){
    }else{
      await groupApp.prepGroupModal(name);
    }
  },

  displayPage: function (items, method, pageNumber, pageSize) {
    let len = items.length;
    let counterlimit = len;
    let counterStart = pageNumber * pageSize;
    let contentEnd = counterStart + pageSize;
    if (contentEnd < len) {
      counterlimit = contentEnd
    }
    for (let i = counterStart; i < counterlimit; i++) {
      method(items[i]);
    }
  },

  getPageSetting: function () {
    if (groupApp.paginationSetting.pageSetting == null) {
      groupApp.paginationSetting.pageSetting = {
        'page_size': groupApp.paginationSetting.defaultPageSize,
        'page_num': 0
      };
      return groupApp.paginationSetting.pageSetting;
    }
    return groupApp.paginationSetting.pageSetting;
  },

  setPageNum: function (num) {
    if (groupApp.paginationSetting.pageSetting == null) {
      groupApp.paginationSetting.pageSetting = {
        'page_size': groupApp.paginationSetting.defaultPageSize,
        'page_num': num
      };
      return;
    }
    groupApp.paginationSetting.pageSetting['page_num'] = num
  },

  setPageSize: function (size) {
    if (groupApp.paginationSetting.pageSetting == null) {
      groupApp.paginationSetting.pageSetting = {
        'page_size': size,
        'page_num': 0
      };
      return;
    }
    groupApp.paginationSetting.pageSetting['page_size'] = size
  },

  paginate: function (items, method) {
    settings = groupApp.getPageSetting();
    groupApp.displayPage(items, method, settings['page_num'], settings['page_size']);
    totalPages = items.length / settings['page_size'];
    displayUpdate("console",`total Pages: ${totalPages}`)
    groupApp.setPageNumber(settings['page_num'], totalPages);
    $("#card-container").foundation();
  },

  setPageNumber: function (selectedPage, totalPages) {
    $("#pagination").find('option').remove();
    for (let i = 0; i < totalPages; i++) {
      if (i == selectedPage) {
        $("#pagination").append(groupUI.selectorOption(i, i + 1, "selected"));
      } else {
        $("#pagination").append(groupUI.selectorOption(i, i + 1, ""));
      }
    }
  },

  changeDisplayPageNum: async function () {
    let e = document.getElementById("pagination");
    let val = e.options[e.selectedIndex].value;
    await $('.reveal-overlay').remove();
    await groupApp.displayCardContainer();
    groupApp.setPageNum(val);
    result = await groupApp.search(groupApp.paginationSetting.query);
    await groupApp.paginate(result, groupApp.displayGroupCard);
  },

  changeDisplayPageSize: async function(){
    groupApp.setPageNum(0);
    let e = document.getElementById("paging");
    let val = e.options[e.selectedIndex].value;
    await $('.reveal-overlay').remove();
    await groupApp.displayCardContainer();
    groupApp.setPageSize(val);
    groupApp.changeDisplayPageNum();
  },

  initiateSearch: async function () {
    let e = document.getElementById("search-select");
    let type = e.options[e.selectedIndex].value;
    let val = document.getElementById("group-search-text").value;
    let query = [
      [type, "contains", val]
    ]
    displayUpdate('console', `groupApp search: ${query}`)
    groupApp.setPageNum(0);
    await $('.reveal-overlay').remove();
    await groupApp.displayCardContainer();
    result = await groupApp.search(query);
    groupApp.saveSearchQuery(query);
    pageSetting = groupApp.getPageSetting();
    displayUpdate("console", pageSetting);
    displayUpdate("console", result);
    await groupApp.paginate(result, groupApp.displayGroupCard);
  },

  search: async function (query) {
    groups = []
    await getGroupList().then(function (element) {
      groups = element['group']
    });
    if (_debug) {
      console.log("query: ", query);
    }
    let result = [];
    if (query == null) {
      result = groups;
    } else {
      result = await groupApp.filterGroups(query, groups);
    }
    return result;
  },

  saveSearchQuery: function (query) {
    groupApp.paginationSetting.query = query
  },

  filterGroups: async function (query, groups) {
    if (_debug) {
      console.log("groupApp.filterGroups: groups.length: ", groups.length);
    }
    let result = [];
    groups.forEach(async (element) => {
      if (groupApp.checkDropdownCriteria(query, element)) {
        result.push(element);
      }
    });
    if (_debug) {
      console.log("searchGroups: result: ", result.length);
    }
    if (_debug) {
      console.log("searchGroups: result: ", result);
    }
    return result;
  },

  checkDropdownCriteria: function (query, element) {
    if (_debug) {
      console.log("checkGroupSearchCriteria: prop[1]: ", query);
    }
    let res = false;
    query.forEach(function (prop) {
      switch (prop[0]) {
        case "name":
          res = groupApp.checkString(prop[1], prop[2], element.name);
          break;
        case "ip":
          if (prop[2] == null || prop[2] == "") {
            res = true;
          } else {
            if (element.members) {
              res = groupApp.checkInArray(prop[2], element.members.lcms);
            }
          }
          break;
        case "description":
          res = groupApp.checkString(prop[1], prop[2], element.description);
          break;
      }
    });
    return res;
  },

  checkString: function (condition, val, str) {
    if (_debug) {
      console.log("checkGroupCondition: condition: ", condition);
      console.log("checkGroupCondition: val: ", val);
      console.log("checkGroupCondition: str: ", str);
    }
    if (val == null || val == "") {
      return true;
    }
    if (str == null) {
      return false;
    }
    if (condition == "equals") {
      let res = val.toUpperCase() === str.toUpperCase();
      if (res == false) {
        return false;
      }
      return true;
    } else if (condition == "contains") {
      let res = str.toUpperCase().includes(val.toUpperCase());
      if (res == false) {
        return false;
      }
      if (_debug) {
        console.log(res, "  ", val)
      }
      return true;
    }
    return true;
  },

  checkInArray: function (val, _array) {
    if (val == null || val == "") {
      return true;
    }
    if (_array == null || _array.length == 0) {
      return false;
    }
    return _array.includes(val);
  },

  createEditContent: function(groupname){
    $(`#replaceable-${groupname}`).replaceWith(`<div id="replaceable">Mama</div>`)
  },

  createMapContent: function(groupname){
    let mymap = L.map(`map-${groupname}`).setView([51.505, -0.09], 15);
    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoiYW1haGFsYSIsImEiOiJjanh1eTZuMHIxYWZjM21udm5hbHA0OXRlIn0.P4ptwzlsmnhOHxm5LO68ig', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox.streets',
    accessToken: 'pk.eyJ1IjoiYW1haGFsYSIsImEiOiJjanh1eTZuMHIxYWZjM21udm5hbHA0OXRlIn0.P4ptwzlsmnhOHxm5LO68ig'
  }).addTo(mymap);
  },

  createGroupList: async function(groupname, str, type){
    let unadded = [];
    let added = [];
    let lcms = [];
    let groupmembers = await groupApp.getGroup(groupname)
    if(str==null || str==""){
      await getLampList().then(function(l){lcms =l});
    }else{
    }
    await lcms.forEach(
      async (element) => {
        if(groupmembers['members'] && groupmembers['members']['lcms']){
          let rep = await groupApp.checkIfAlreadyPresent(groupmembers['members']['lcms'], element['ip']);
          if (!rep) {
            unadded.push(element);
          }else{
            added.push(element);
          }
        }else{
          unadded.push(element);
        }
      }
    );
    return [added,unadded];
  },

  getGroup: async function(groupName){
    let groups = [];
    let members = null;
    await getGroupList().then(function(grps) {
      groups = grps["group"];
    });
    await groups.forEach(async(group)=>{
      if (group['name'] ==groupName){
        members = group;
      }
    });
    return members;
  }, 

  checkIfAlreadyPresent: async function( list, element){
    for(let i=0; i<list.length; i++){
      if(list[i].toUpperCase()===element.toUpperCase()){
        return true;
      }
    }
    return false;
  },

  populateGroupList: async function (groupName){
    $(`#generate-form-wait-${groupName}`).show();
    let radioValue = await $(`input[name="edit-1radio-${groupName}}"]:checked`).val();
    let list = await groupApp.createGroupList(groupName, "", "");
    $(`#added-lcm-${groupName}`).empty();
    $(`#unadded-lcm-${groupName}`).empty();
    list[0].forEach(async(ele)=>{$(`#added-lcm-${groupName}`).append(groupUI.selectorOption(ele['ip'], ele[radioValue], ""));});
    list[1].forEach(async(ele)=>{$(`#unadded-lcm-${groupName}`).append(groupUI.selectorOption(ele['ip'], ele[radioValue], ""));});
    $(`#generate-form-wait-${groupName}`).hide();
  },

  searchDisplayValueInSelector: async function(id, value){
    $(`#${id} > option`).each(function() {
      if(this.text.toUpperCase().includes(value.toUpperCase())){
        this.style.display = "";
      }else{
        this.style.display = "none";
      }
  });
  },

  addLcmInGroup: function(groupName){
    let selected = $("option:selected", $(`#unadded-lcm-${groupName}`));
    for(let i=0;i<selected.length;i++){
      $(`#added-lcm-${groupName}`).append(groupUI.selectorOption(selected[i].value, selected[i].text, ""));
    }
    $('option:selected', $(`#unadded-lcm-${groupName}`)).remove();
  },

  removeLcmInGroup: function(groupName){
    let selected = $("option:selected", $(`#added-lcm-${groupName}`));
    for(let i=0;i<selected.length;i++){
      $(`#unadded-lcm-${groupName}`).append(groupUI.selectorOption(selected[i].value, selected[i].text, ""));
    }
    $('option:selected', $(`#added-lcm-${groupName}`)).remove();
  },

  saveGroupChanges: async function(groupName){
    new_state = []
    added = []
    removed = []
    await $(`#added-lcm-${groupName} > option`).each(function(){
      new_state.push(this.value);
    });
    old_state = [];
    group = await groupApp.getGroup(groupName);
    if(group['members'] && group['members']['lcms']){
      old_state = group['members']['lcms'];
    }
    extras = await groupApp.findExtras(old_state,new_state);
    newDescription = await document.getElementById(`group-desc-${group.name}`).value;
    isDescriptionChanged = await groupApp.descriptionChange(group, newDescription);
    removeRequest = null;
    addRequest = null;
    changes = {};
    if(extras[0].length>0 || isDescriptionChanged){
      let removal = {};
      if(extras[0].length>0){
        removal["members"] = {"lcms": extras[0]};
      }
      if(isDescriptionChanged && newDescription===""){
        removal["description"] = await document.getElementById(`group-desc-${group.name}`).value;
      }
      changes["remove"] = removal;
    }
    if(extras[1].length>0 || isDescriptionChanged){
      let addition = {}
      if(extras[1].length>0){
        addition["members"] = {"lcms":extras[1]};
      }
      if(isDescriptionChanged && newDescription!=""){
        addition["description"] = await document.getElementById(`group-desc-${group.name}`).value;
      }
      changes["add"] = addition;
    }
    if("add" in changes || "remove" in changes){
      groupApp.sendGroupChangeRequest(groupName, changes);
    }
  },

  descriptionChange: function(group, new_txt){
    old_txt = null;
    if(group.description){
      old_txt = group.description;
    }
    if(old_txt){
      if(old_txt===new_txt){
        return false;
      }
      return true;
    }
    if(new_txt ==null || new_txt===""){
      return false;
    }
    return true;
  },

  findExtras: function(list1, list2){
    list1 = list1.sort();
    list2 = list2.sort();
    l1_extra = [];
    l2_extra = [];
    let i = 0;
    let j = 0;
    while(i<list1.length || j<list2.length){
      if(i>=list1.length){
        l2_extra.push(list2[j]);
        j+=1;
        continue;
      }
      if(j>=list2.length){
        l1_extra.push(list1[i]);
        i+=1;
        continue;
      }
      if(list2[j]<list1[i]){
        l2_extra.push(list2[j]);
        j+=1;
      }else if(list2[j]>list1[i]){
        l1_extra.push(list1[i]);
        i+=1;
      }else{
        i+=1;
        j+=1;
      }
    }
    return [l1_extra, l2_extra];
  },

  sendGroupChangeRequest: async function(groupName, body){
    wait_period = 10000;
    await group_name_put(groupName, body, function(){
      groupApp.showCalloutForMS('.group-update-success',wait_period);
    }, function(){
      groupApp.showCalloutForMS('.group-update-fail',wait_period);
    })
    await refreshGroupList();
    groupApp.populateGroupList(groupName);
  },

  sleep: function(time) {
    return new Promise((resolve) => setTimeout(resolve, time));
  },

  showCalloutForMS: async function(callout,ms){
    await $(callout).show();
    await groupApp.sleep(ms);
    $(`${callout} .close-button`).trigger('close');
  },

  saveGroupProfileChange: function(groupName){
    let display_card_timeout = 10000;
    let new_value = document.getElementById(`group-profile-${groupName}`).value;
    displayUpdate(new_value);
    let isProfileChanged = groupApp.checkProfileChange(groupName, new_value);
    if(isProfileChanged){
      if(new_value ===""){
        group_profile_change(groupName, {"action": "remove", "profile": new_value}, function(){
          groupApp.showCalloutForMS(".group-profile-success", display_card_timeout);
        }, function(){
          groupApp.showCalloutForMS(".group-profile-fail", display_card_timeout);
        });
      }
      else{
        group_profile_change(groupName, {"action": "update", "profile": new_value}, function(){
          groupApp.showCalloutForMS(".group-profile-success", display_card_timeout);
        }, function(){
          groupApp.showCalloutForMS(".group-profile-fail", display_card_timeout);
        });
      }
    }
  },

  checkProfileChange: async function(groupName, newValue){
    let groups = [];
    let res = false;
    await getGroupList().then(function(grps) {
      groups = grps["group"];
    });
    await groups.forEach(async(group)=>{
      if (group['name'] == groupName){
        if('profile' in group){
          if(newValue==group['profile']){
            res = false;
          }else{
            res = true;
          }
        } else{
          if(newValue==""){
            res = false;
          }else{
            res = true;
          }
        }
      }
    });
    return res;
  },

  startOTA: function(group_name){
    display_card_timeout = 100000;
    let otalink = document.getElementById(`group-ota-${group_name}`).value;
    if(otalink===""){
      return;w
    }
    group_otau(group_name, {"firmware-file": otalink},function(){
      groupApp.showCalloutForMS(".group-ota-success", display_card_timeout);
    },function(){
      groupApp.showCalloutForMS(".group-ota-fail", display_card_timeout);
    });
  }

}

$(document).on('keypress', function (e) {
  if (e.which == 13) {
    if (e.target == document.getElementById("group-search-text")) {
      groupApp.initiateSearch();
    }
    if(e.target.className==="search-added"){
      id = `added-lcm-${e.target.id.split("-")[3]}`;
      value = e.target.value;
      groupApp.searchDisplayValueInSelector(id, value); 
    }
    if(e.target.className==="search-unadded"){
      id = `unadded-lcm-${e.target.id.split("-")[3]}`;
      value = e.target.value;
      groupApp.searchDisplayValueInSelector(id, value); 
    }
  }
});