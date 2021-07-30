let lcmUI = {  
  lcmModel: function(lamp) {
    return `<div class="large reveal" id="model-${lamp.key}" data-reveal>
  <div class="grid-x medium-up-2">
    <div class="cell">
      <a href="https://www.idt.com/"><img class="menu-logo" alt="IDT - Integrated device Tachnology"
      src="images/new_idt.png"></a><br /><br />
    </div>
    <div class="cell">
    <p class="idt-heading model-heading">Luminaire</p>
  </div>
</div>   
<!-- Lamp Data -->
<div class="grid-y grid-padding-y" style="border-top: solid 2px; border-color: #e6e6e6;">
  <div class="grid-x medium-up-2">
    <div class="cell" style="padding-bottom: 5px;">
      <b>Serial Number: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.key}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>IPv6: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.ip?lamp.ip:"--"}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>Hub Id: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.hubid?lamp.hubid:"--"}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>Longitude: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.longitude?lamp.longitude:"--"}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>Latitude: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.latitude?lamp.latitude:"--"}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>Current: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.current?lamp.current:"--"}</u><br />
    </div>
    <div class="cell" style="padding-bottom: 5px;">
      <b>Voltage: </b><br />
      <u style="text-decoration-color: #e6e6e6; padding-left: 10px;">${lamp.valtage?lamp.voltage:"--"}</u><br />
    </div>
  </div>
  <!-- Dimming Functionality-->
  <div class="grid-x  small-up-1 medium-up-2 large-up-3"
  style="border-top: solid 2px; border-color: #e6e6e6;">
  <div class="cell" style="padding: 1rem"><button  onClick="dim ( '${lamp.ip}', 100 )" type="button"
  class="expanded success button">on</button></div>
  <div class="cell" style="padding: 1rem"><button  onClick="dim ( '${lamp.ip}', 0 )" type="button"
  class="expanded alert button">Off</button></div>
  <!-- <div class="cell" style="padding: 1rem"> -->
  <div class="cell grid-container">
    <div class="grid-x">
      <div class="cell small-8">
        <div id="modelSlider-${lamp.key}" class="slider" data-slider data-initial-start="100.0" data-step="0.1">
          <span id="modelSliderHandleIn1" class="slider-handle" data-slider-handle role="slider" tabindex="1"
          aria-controls="modelSliderOut-${lamp.key}"></span>
          <span class="slider-fill" data-slider-fill></span>
        </div></div>
        <div class="cell small-1"></div>
    <div class="cell small-3"><input type="number" id="modelSliderOut-${lamp.key}"></div>         
  </div>
  </div>
  <script type="text/javascript" language="javascript">
    $(document).ready(function(){
      let model_loaded = false;
    $('#modelSlider-${lamp.key}').on('changed.zf.slider', function() {
      if(model_loaded){
        let dim_val = $(this).children('.slider-handle').attr('aria-valuenow');
          dim("${lamp.ip}",dim_val);
      }
      model_loaded = true;
      });
      });
  </script>
  </div>
  </div>
  <div class="grid-x  small-up-1 medium-up-2 large-up-3" style="border-top: solid 2px; border-color: #e6e6e6;">
    <div class="cell" style="padding: 1rem">
      <h4>Over the Air update</h4>
      <p>To update the luminaire please paste the provided update link and press enter</p>
    </div>
    <div class="cell" style="padding: 1rem">
      <input id="otau-${lamp.key}" type="text" placeholder="given OTAU link" required>
    </div>
    <div class="cell" style="padding: 1rem">
      <button onclick="lcmApp.otau('${lamp.ip}','${lamp.key}')" class="primary button" >Update Luminaire</button>
    </div>
  </div>
  <div class="grid-x">
    <div class="medium-5 cell">
      <div class="lcm-ota-success callout success medium-4 small-12 cell" data-closable style="display: none">
        <p style="color: green;">Successfully initiated OTA Update</p>
        <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    </div>
    <div class="medium-5 cell">
      <div class="lcm-ota-fail callout alert medium-4 small-12 cell" data-closable style="display: none">
        <p style="color: #CC4B37;">Failed to initiate OTA Update</p>
        <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    </div>
  </div>
  <div class="grid-x  small-up-1 medium-up-2 large-up-3"
  style="border-top: solid 2px; border-color: #e6e6e6;">
  <div class="cell" style="padding: 1rem">
  <h4>Decommission Luminaire</h4>
  </div>
  <div class="cell" style="padding: 1rem">
    <button class="expanded alert button" data-open="decommission-model-${lamp.key}" data-close aria-label="Close modal"')">Decommission</button>
  </div>
  </div>
  <!-- luminaire decommission -->
  <div class="large reveal" id="decommission-model-${lamp.key}" data-reveal>
    <div class="grid-x ">
      <div class="cell medium-3 large-4">
        <a href="https://www.idt.com/"><img class="menu-logo" alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
        </div>
        <div class="cell medium-9 large-8">
          <p class="idt-heading model-heading">Decommission</p>
          <p class="idt-heading model-heading">Luminaire</p>
        </div>
      </div>
      <div class="grid-x  small-up-1 medium-up-2 large-up-3"
      style="border-top: solid 2px; border-color: #e6e6e6;">
      <a>You are about to decommission luminaire: ${lamp.key}. Which means you will not be able to turn the luminaire
          on and off unless you re commission it again. In order to decommission the luminaire,
          please type the Serial number of the luminaire in the input and click decommission</a>
      <div class="cell" style="padding: 1rem">
      <label><a>Confirm:</a>
      <input id="decommission-${lamp.key}" type="text" aria-errormessage="decommission-error-${lamp.key}" placeholder="${lamp.key}" required>
      <span class="form-error" id="decommission-error-${lamp.key}" style="display: none;">
        Please check the serial number and type again!
      </span>
      </label>
      </div>
      <div class="cell" style="padding: 1rem">
        <br/> 
        <button class="expanded alert button" onclick="decommissionlcm('${lamp.key}','${lamp.ip}')">Decommission</button>
      </div>
      <div class="cell" style="padding: 1rem">
      <br/> 
      <button class="expanded success button" data-close aria-label="Close modal" >Cancel</button>
      </div>
    </div>
    <div id="decommission-callout-success-${lamp.key}" class="callout success data-closable decommission-success-callout" style="display: none">
      <h5>Luminaire has been successfully Decommissioned</h5>
      <p>You can close the close this callout and go to the dashboard</p>
    </div>
    <div id="decommission-callout-fail-${lamp.key}" class="callout alert data-closable decommission-success-callout" style="display: none">
      <h5>unable to decommission</h5>
      <p>Something went went Wrong</p>
    </div>
  <!-- Model Close Button-->
  <button class="close-button" data-close aria-label="Close modal" type="button">
  <span aria-hidden="true">&times;</span>
  </button>
  </div>
  <!-- Model Close Button-->
  <button class="close-button" data-close aria-label="Close modal" type="button">
    <span aria-hidden="true">&times;</span>
  </button>
</div>`;
},
      
  lcmCard: function(lamp) {
        return `<!-- Card Starting-->
<div id="lamp-cell-${lamp.key}" class="cell">
  <div class="card float-center lamp-card">
    <div class="grid-x  card-header-cell">
      <div class="cell small-10">
        <b type="button" data-toggle="offCanvas-${lamp.key}" class="expanded button card-heading"
        style="padding-top: 1em; padding-bottom: 1 em;">IPv6: ${lamp.ip}</b>
        </div>
        <div class="cell small-2">
          <img type="button" onclick="lazyModelPrep('${lamp.key}')" data-open="model-${lamp.key}" class="expand-logo" alt="expand"
          src="images/icons8_expand_96px.png">
        </div>
      </div>
      <!-- Model Start -->
      <div class="large reveal" id="model-${lamp.key}" data-reveal>
      </div>
    <!-- Model End -->
    <!-- Card Section -->
    <div class="card-section" style="padding: 0">
      <div class="off-canvas-wrapper">
      <!-- Off Canvas Content-->
        <div class="off-canvas-absolute position-bottom card-hidden-content" id="offCanvas-${lamp.key}"
          data-off-canvas style="background-color: white">
          <p><b>IPv6: </b>${lamp.ip?lamp.ip:"--"}</p>
          <hr />
          <p><b>Hub Id: </b>${lamp.hubid?lamp.hubid:"--"}</p>
          <hr />
          <p><b>Longitude: </b>${lamp.longitude?lamp.longitude:"--"}</p>
          <hr />
          <p><b>Latitude: </b>${lamp.latitude?lamp.latitude:"--"}</p>
          <hr />
          <p><b>Current: </b>${lamp.current?lamp.current:"--"}</p>
          <hr />
          <p><b>Voltage: </b>${lamp.valtage?lamp.voltage:"--"}</p>
        </div>
        <!-- In Canvas Content-->
        <div class="off-canvas-content" data-off-canvas-content style="padding: 1rem">
          <div class="grid-x">
            <div onClick="dim ( '${lamp.ip}', 100 )" type="button" class="success button cell small-5">On</div>
            <div class="cell small-2"></div>
            <div onClick="dim ( '${lamp.ip}', 0 )" type="button" class="alert button cell small-5">Off</div>
          </div>
          <div class="grid-y">
            <div class="cell small-8 medium-8 large-8">
              <div id="lampSlider-${lamp.key}" class="slider" data-slider data-initial-start="100.0" data-step="0.1">
                <span class="slider-handle" data-slider-handle role="slider" tabindex="1"
                  aria-controls="lampSliderOutput-${lamp.key}"></span>
                <span class="slider-fill" data-slider-fill></span>
              </div>
            </div>
            <div class="cell small-4 medium-4 large-4">
              <input type="number" id="lampSliderOutput-${lamp.key}">
            </div>
          </div>
          <div class="grid-x">
            <div  type="button" class="cell small-5"><input id="rgb-card-${lamp.key}" type="color"
            value="${lcmApp.rgbToHex(lamp.rgb)}" style="padding: 0"></div>
            <div class="cell small-2"></div>
            <div onclick="lcmApp.setColor('${lamp.ip}','${lamp.key}')" type="button" class="primary button cell small-5">Set Color</div>
          </div>
          <script type="text/javascript" language="javascript">        
            $(document).ready(function(){
              let card_loaded = false;
              $('#lampSlider-${lamp.key}').on('changed.zf.slider', function() {
                if (card_loaded){
                let dim_val = $(this).children('.slider-handle').attr('aria-valuenow');
                dim("${lamp.ip}",dim_val);
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
    src="images/icons8_lights_96px_1.png"></a></li>
    <li><label id="max-results">Results Per Page</label>
    <select id="paging" onchange="selectPageSize()">
    </select>
    </li>
  </ul>
</div>
<div class="top-bar-right">
  <ul class="menu">
    <li>
      <select id="search-select">
        <option value="lcmid">Serial Number</option>
        <option value="hubid">Hub id</option>
        <option value="lcmip">IPv6</option>
      </select>
    </li>
    <li><input id="search-text" type="search" placeholder="Search"></li>
    <li><button type="button" onclick="searchLcm()" class="button">Search</button></li>
  </ul>
</div>
</div>`;
  },

lcmCardContainer: function(){
  return `<section id="card-container">
  <div class="grid-container fluid">
    <div class="small-4 cell"></div>
    <div id="lamp-card-container" 
      class="grid-x grid-padding-x grid-padding-y small-up-1 medium-up-2 large-up-3">
      <!-- Lamp Cards go here-->
    </div>
  </div>
</section>`;
  },

  canvas: function(){
    return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div id="sub-bar" class="top-bar">
  </div>
  <!-- Lamp-Cards Section -->
  <section id="card-container">
  </section>
  <!-- Pagination -->
  <nav aria-label="Pagination">
  <div class="float-center" style="width: 70px"><label>Page No.</label></div>
  <select id="pagination" class="float-center" onchange="selectPage()">
  </select>
  </nav>
</div>`;
  },

  selectorOption: function(value, displayValue, selected){
    return `<option value="${value}" ${selected}>${displayValue}</option>`;
  }
}