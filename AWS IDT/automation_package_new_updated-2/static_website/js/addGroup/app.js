addGroupApp = {
  start: function(){
    addGroupApp.prepAddGroup();
  },

  prepAddGroup: function(){
    $("#ice-content").replaceWith(addGroupUI.canvas());
  },

  populateGroupLcmList: async function (){
    $(`#generate-form-wait`).show();
    let radioValue = await $(`input[name="edit-1radio"]:checked`).val();
    let list = await addGroupApp.createGroupList();
    $(`#added-lcm`).empty();
    $(`#unadded-lcm`).empty();
    list.forEach(async(ele)=>{$(`#unadded-lcm`).append(addGroupUI.selectorOption(ele['ip'], ele[radioValue], ""));});
    $(`#generate-form-wait`).hide();
  },

  createGroupList: async function(){
    // This string is to check the field in search area
    let lcms = [];
    await getLampList().then(function(l){lcms =l});
    return lcms;
  },

  getGroup: async function(groupName){
    let groups = [];
    let grp = null;
    await getGroupList().then(function(grps) {
      groups = grps["group"];
    });
    await groups.forEach(async(group)=>{
      if (group['name'] ==groupName){
        grp = group;
      }
    });
    return grp;
  },

  addLcmInGroup: function(){
    let selected = $("option:selected", $(`#unadded-lcm`));
    for(let i=0;i<selected.length;i++){
      $(`#added-lcm`).append(addGroupUI.selectorOption(selected[i].value, selected[i].text, ""));
    }
    $('option:selected', $(`#unadded-lcm`)).remove();
  },

  removeLcmInGroup: function(){
    let selected = $("option:selected", $(`#added-lcm`));
    for(let i=0;i<selected.length;i++){
      $(`#unadded-lcm`).append(addGroupUI.selectorOption(selected[i].value, selected[i].text, ""));
    }
    $('option:selected', $(`#added-lcm`)).remove();
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

  submit: async function(){
    request = {}
    name = await document.getElementById("group-name").value;
    description = await document.getElementById("group-description").value;
    isValidName = await addGroupApp.validateGroupName(name);
    if(isValidName){
      request['name'] = name;
    }
    isValidDescription = true;
    if(description == null || description!=""){
      isValidDescription = addGroupApp.validateDescription(description);
      if(isValidDescription){
        request['description'] = description;
      }
    }
    lcms = await addGroupApp.getSelectedLcm();
    if(lcms.length>0){
      request['members'] = {"lcms":lcms}
    }
    if(isValidName && isValidDescription){
      addGroupApp.sendGroupCreateRequest(request);
    }
    
  },

  getSelectedLcm: async function(){
    lcms = []
    await $(`#added-lcm > option`).each(function(){
      lcms.push(this.value);
    });
    return lcms;
  },

  validateGroupName: async function(name){
    if(typeof name == 'undefined' || name==null || name=== ""){
      $(".form-error-callout").show();
      $("#groupError1").show();
      return false;
    }
    grp = null
    await addGroupApp.getGroup(name).then(function(result){
      grp = result;
    });
    console.log(grp);
    if(grp!=null){
      $("#groupError2").show();
      return false;
    }
    let regexp = /^[a-zA-Z0-9\_]{1,40}$/;
    if (name.search(regexp) == -1){
      $(".form-error-callout").show();
      $("#groupError1").show();
      return false;
    }
    return true;
  },

  validateDescription: async function(description){
    let regexp = /[a-zA-Z0-9\_\+\-\.]{1,500}/g;
    console.log(description);
    if (description.search(regexp) == -1){
      $(".form-error-callout").show();
      $("#group-descError1").show();
      return false;
    }
    return true;
  },

  clearForm: function(){
    $(".form-error-callout").hide();
    $(".submit-error-callout").hide();
    $(".submit-success-callout").hide();
    $("#groupError1").hide();
    $("#groupError2").hide();
    $("#group-descError1").hide();
    $("#group-name").val("");
    $("textarea").val("");
    addGroupApp.removeAllLcm();
  },

  removeAllLcm: async function(){
    lcms = await $(`#added-lcm > option`)
    for(let i=0;i<lcms.length;i++){
      $(`#unadded-lcm`).append(addGroupUI.selectorOption(lcms[i].value, lcms[i].text, ""));
    }
    $(`#added-lcm > option`).remove();
  },

  sendGroupCreateRequest: function(request){
    console.log("reached send Group create Request");
    console.log(request);
    ifSuccess = function(){
      $(".submit-success-callout").show();
    }
    ifFail = function(){
      $(".submit-error-callout").show();
    }
    addGroup(request, ifSuccess, ifFail);
  }

}

$(document).on('keypress', function (e) {
  if (e.which == 13) {
    if(e.target.className==="create-search-added"){
      id = `added-lcm`;
      value = e.target.value;
      addGroupApp.searchDisplayValueInSelector(id, value); 
    }
    if(e.target.className==="create-search-unadded"){
      id = `unadded-lcm`;
      value = e.target.value;
      addGroupApp.searchDisplayValueInSelector(id, value); 
    }
  }
});