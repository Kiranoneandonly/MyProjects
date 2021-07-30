let groupUI = {  
  
  
groupModal: function(group){
  return `
  <div class="large reveal" id="model-${group.name}" data-reveal>
    <div class="grid-x medium-up-2">
      <div class="cell show-for-medium">
        <a href="https://www.idt.com/"><img class="menu-logo" alt="IDT - Integrated device Tachnology"
          src="images/new_idt.png"></a><br /><br />
      </div>
      <div class="cell">
        <p class="idt-heading model-heading">Group</p>
      </div>
    </div>

    <!-- Tabs List Start-->
    <ul class="tabs" data-deep-link="true" data-update-history="false" data-deep-link-smudge="true" data-deep-link-smudge-delay="500" data-tabs id="tabs-${group.name}">
      <li class="tabs-title is-active"><a href="#panel1-${group.name}" aria-selected="true"><b>Details</b></a></li>
      <li class="tabs-title"><a href="#panel2-${group.name}"><b>Edit</b></a></li>
      <!-- <li class="tabs-title"><a href="#panel3-${group.name}"><b>Monitor</b></a></li> -->
      <li class="tabs-title"><a href="#panel4-${group.name}"><b>OTA Update</b></a></li>
    </ul>
    <script>
      $('#tabs-${group.name}').on('change.zf.tabs', function(event, tab) {
        if($('#panel2-${group.name}:visible').length){
          // groupApp.createEditContent('${group.name}');
        }
        if($('#panel3-${group.name}:visible').length){
          groupApp.createMapContent('${group.name}');
        }
      });
    </script>
    <!-- Tabs List End-->

    <!-- Tabs Content Start-->
    <div class="tabs-content" data-tabs-content="tabs-${group.name}">

      <!-- Detail Tab Start-->
      <div class="tabs-panel is-active" id="panel1-${group.name}">
        
        <div class="grid-y grid-padding-y">
          <!-- Lamp Data Start-->
          <div class="grid-x large-up-2">
            <div class="cell" style="padding-bottom: 5px;">
              <b>Group Name: </b><br />
              <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${group.name}</u><br />
            </div>
            <div class="cell" style="padding-bottom: 5px;">
              <b>Description: </b><br />
              <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${group.description}</u><br />
            </div>
          </div>
          <!-- Lamp Data End-->

          <!-- Lamp Control Start-->
          <div class="grid-x  small-up-1 medium-up-2 large-up-3" style="border-top: solid 2px; border-color: #e6e6e6;">
            <div class="cell" style="padding: 1rem">
              <button  onClick="dim ( '${group.name}', 100 )" type="button" class="expanded success button">on</button>
            </div>
            <div class="cell" style="padding: 1rem">
              <button  onClick="dim ( '${group.name}', 0 )" type="button" class="expanded alert button">Off</button>
            </div>
            <div class="cell grid-container">
              <div class="grid-x">
                <div class="cell small-8">
                  <div id="modelSlider-${group.name}" class="slider" data-slider data-initial-start="100.0" data-step="0.1">
                    <span id="modelSliderHandleIn1" class="slider-handle" data-slider-handle role="slider" tabindex="1"
                      aria-controls="modelSliderOut-${group.name}"></span>
                    <span class="slider-fill" data-slider-fill></span>
                  </div>
                </div>
                <div class="cell small-1"></div>
                <div class="cell small-3"><input type="number" id="modelSliderOut-${group.name}"></div>
              </div>
            </div>
            <script type="text/javascript" language="javascript">
              $(document).ready(function(){
              let model_loaded = false;
              $('#modelSlider-${group.name}').on('changed.zf.slider', function() {
                if(model_loaded){
                  let dim_val = $(this).children('.slider-handle').attr('aria-valuenow');
                  group_dim("${group.name}",dim_val);
                }
                model_loaded = true;
                });
              });
            </script>
          </div>
          <!-- Lamp Control End-->
        </div>
      </div>
      <!-- Detail Tab End-->

      <!-- Edit Tab Start-->
      <div class="tabs-panel" id="panel2-${group.name}">
        <!-- <div id="replaceable-${group.name}">
          <img class="float-center" alt="Busy" src="images/805_anticlock.gif">
        </div> -->
        <div class="grid-y grid-padding-y">
          <div class="grid-x grid-padding-x">
            <div class="float-center">
              <fieldset class="small-12 cell">
                <legend>Choose Form Type <img class="side-menu-img" id="generate-form-wait-${group.name}"alt="User" src="images/loading1.gif" style="display: none"></legend>
                <input type="radio" name="edit-1radio-${group.name}}" value="ip" id="edit-1radio1-${group.name}}" checked required><label for="edit-1radio1-${group.name}}">IP</label>
                <input type="radio" name="edit-1radio-${group.name}}" value="key" id="edit-1radio2-${group.name}}" required><label for="edit-1radio2-${group.name}}">Serial</label> 
                <button onclick="groupApp.populateGroupList('${group.name}')" class="primary button small"><b>Generate</b></button>
              </fieldset>
            </div>
          </div>
          <div class="grid-x grid-padding-x">
            <div class="medium-5 cell">
              <label>Unadded Luminaires:
                <input type="search" class="search-unadded" id="search-unadded-lcm-${group.name}" placeholder="Search luminaire">
                <select multiple id="unadded-lcm-${group.name}">
                </select>
              </label>
            </div>
            <div class="medium-2 cell">
              <div class="show-for-medium" style="padding-top: 60px;"></div>
              <img onclick="groupApp.addLcmInGroup('${group.name}')" class="side-menu-img generate-form-wait" alt="User" src="images/plus_96px.png">
              <img onclick="groupApp.removeLcmInGroup('${group.name}')" class="side-menu-img generate-form-wait" alt="User" src="images/minus_96px.png">
            </div>
            <div class="medium-5 cell">
              <label>Added Luminaires:
                <input type="search" class="search-added" id="search-added-lcm-${group.name}" placeholder="search Luminaire">
                <select multiple id="added-lcm-${group.name}">
                </select>
              </label>
            </div>
          </div>
          <div>
              <label>Desciption:
              <textarea type="text" id="group-desc-${group.name}" placeholder="Group Deccription">${group.description?group.description:""}</textarea>
              </label>
              <div class="grid-x grid-padding-x">
                <div class="group-update-success callout success medium-4 small-12 cell" data-closable style="display: none">
                  <p style="color: green;">Group Update Success</p>
                  <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                    <span aria-hidden="true">&times;</span>
                  </button>
                </div>
                <div class="group-update-fail callout alert medium-4 small-12 cell" data-closable style="display: none">
                  <p style="color: #CC4B37;">Group Update Failed</p>
                  <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                    <span aria-hidden="true">&times;</span>
                  </button>
                </div>
              </div>
              <button onclick="groupApp.saveGroupChanges('${group.name}')" class="primary button float-right">Save Changes</button>
          </div>
          <div class="grid-x grid-padding-x" style="border: 1px">
            <div class="medium-2 cell">
              <label>Set Profile:</label>
            </div>
            <div class="medium-3 cell">
              <input type="text" id="group-profile-${group.name}" placeholder="Profile Name" value="${group.profile?group.profile:""}">
            </div>
            <div class="medium-2 cell">
              <button onclick="groupApp.saveGroupProfileChange('${group.name}')" class="primary button float-right">Save Profile</button>
            </div>
            <div class="medium-5 cell">
              <div class="group-profile-success callout success medium-4 small-12 cell" data-closable style="display: none">
                <p style="color: green;">Profile Successfully changed</p>
                <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
            </div>
            <div class="medium-5 cell">
              <div class="group-profile-fail callout alert medium-4 small-12 cell" data-closable style="display: none">
                <p style="color: #CC4B37;">Unable to change Profile</p>
                <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Edit Tab End-->

      <!-- Monitor Tab Start-->
      <!-- <div class="tabs-panel" id="panel3-${group.name}">
        <p>Monitor the group Here</p>
        <div class="openmap" id="map-${group.name}">
        </div>
      </div> -->
      <!-- Monitor Tab End-->

      <!-- OTAU Tab Start-->
      <div class="tabs-panel" id="panel4-${group.name}">
        <div class="grid-x grid-padding-x" style="border: 1px">
          <div class="medium-2 cell">
            <label>OTA Update:</label>
          </div>
          <div class="medium-3 cell">
            <input type="text" id="group-ota-${group.name}" placeholder="Paste the given OTA link">
          </div>
          <div class="medium-2 cell">
            <button onclick="groupApp.startOTA('${group.name}')" class="primary button float-right">Start OTA</button>
          </div>
          <div class="medium-5 cell">
            <div class="group-ota-success callout success medium-4 small-12 cell" data-closable style="display: none">
              <p style="color: green;">Over The Air Update Successfully Initiated</p>
              <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>
          <div class="medium-5 cell">
            <div class="group-profile-fail callout alert medium-4 small-12 cell" data-closable style="display: none">
              <p style="color: green;">Over The Air Update Failed to Initiate</p>
              <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- OTAU Tab End-->

    </div>
    <!-- Tabs Content End-->



    <!-- Model Close Button-->
    <button class="close-button" data-close aria-label="Close modal" type="button">
      <span aria-hidden="true">&times;</span>
    </button>
  </div>
  `;
},

  groupCard: function(group) {
        return `<!-- Card Starting-->
<div id="group-cell-${group.name}" class="cell">
  <div class="card float-center lamp-card">
    <div class="grid-x  card-header-cell">
      <div class="cell small-10">
        <b type="button" data-toggle="offCanvas-${group.name}" class="expanded button card-heading"
        style="padding-top: 1em; padding-bottom: 1 em;">Group Name: ${group.name}</b>
        </div>
        <div class="cell small-2">
          <img type="button" onclick="groupApp.lazyModelPrep('${group.name}')" data-open="model-${group.name}" class="expand-logo" alt="expand"
          src="images/icons8_expand_96px.png">
        </div>
      </div>
      <!-- Model Start-->
      <div class="large reveal" id="model-${group.name}" data-reveal>
      </div>
    <!-- Model End-->
    <!-- Card Section-->
    <div class="card-section" style="padding: 0">
      <div class="off-canvas-wrapper">
      <!-- Off Canvas Content-->
        <div class="off-canvas-absolute position-bottom card-hidden-content" id="offCanvas-${group.name}"
          data-off-canvas style="background-color: white">
          <p><b>Group Name: </b>${group.name}</p>
          <hr />
          <p><b>Description: </b>${group.description}</p>
        </div>
        <!-- In Canvas Content-->
        <div class="off-canvas-content" data-off-canvas-content style="padding: 1rem">
          <div onClick="group_dim ( '${group.name}', 100 )" type="button" class="success expanded button">On</div>
            <div onClick="group_dim ( '${group.name}', 0 )" type="button" class="alert expanded button">Off</div>
              <div class="grid-y">
                <div class="cell small-8 medium-8 large-8">
                  <div id="lampSlider-${group.name}" class="slider" data-slider data-initial-start="100.0" data-step="0.1">
                    <span class="slider-handle" data-slider-handle role="slider" tabindex="1"
                    aria-controls="lampSliderOutput-${group.name}"></span>
                    <span class="slider-fill" data-slider-fill></span>
                  </div>
                </div>
              <div class="cell small-4 medium-4 large-4">
                <input type="number" id="lampSliderOutput-${group.name}">
              </div>
            </div>
            <script type="text/javascript" language="javascript">        
              $(document).ready(function(){
                let card_loaded = false;
                $('#lampSlider-${group.name}').on('changed.zf.slider', function() {
                  if (card_loaded){
                  let dim_val = $(this).children('.slider-handle').attr('aria-valuenow');
                  group_dim("${group.name}",dim_val);
                }
                card_loaded = true;
              });
            });
            </script>
          </div>
        </div>
      </div>
    </div>
  </div>
<!-- Card Ending -->`;
  },

subMenu: function(){
  return `<div id="sub-bar" class="top-bar">
<div class="top-bar-left">
  <ul class="menu">
    <li><a><img class="menu-logo" alt="lamp"
    src="images/icons8_group_objects_96px.png"></a></li>
    <li><label id="max-results">Results Per Page</label>
    <select id="paging" onchange="groupApp.changeDisplayPageSize()">
    </select>
    </li>
  </ul>
</div>
<div class="top-bar-right">
  <ul class="menu">
    <li>
      <select id="search-select">
        <option value="name">Group Name</option>
        <option value="ip">Lamp IP</option>
        <option value="description">Description</option>
      </select>
    </li>
    <li><input id="group-search-text" type="search" placeholder="Search"></li>
    <li><button type="button" onclick="groupApp.initiateSearch()" class="button">Search</button></li>
  </ul>
</div>
</div>`;
  },

groupCardContainer: function(){
  return `<section id="card-container">
  <div class="grid-container fluid">
    <div class="small-4 cell"></div>
    <div id="group-card-container" 
      class="grid-x grid-padding-x grid-padding-y small-up-1 medium-up-2 large-up-3">
      <!-- Group Cards go here-->
    </div>
  </div>
</section>`;
  },

  canvas: function(){
    return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div id="sub-bar" class="top-bar">
  </div>
  <!-- Group-Cards Section -->
  <section id="card-container">
  </section>
  <!-- Pagination -->
  <nav aria-label="Pagination">
  <div class="float-center" style="width: 70px"><label>Page No.</label></div>
  <select id="pagination" class="float-center" onchange="groupApp.changeDisplayPageNum()">
  </select>
  </nav>
</div>`;
  },

  selectorOption: function(value, displayValue, selected){
    return `<option value="${value}" ${selected}>${displayValue}</option>`;
  }
}