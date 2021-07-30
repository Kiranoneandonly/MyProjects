let loadlcmUI = {
  canvas: function(){
    return `
    <div id="ice-content" class="off-canvas-content" data-off-canvas-content>
      <div id="sub-bar" class="top-bar" style="margin-bottom: 12px;">
        <div class="top-bar-left">
          <a><img class="menu-logo" alt="lamp"
            src="images/load_lcm.png"></a>
        </div>
        <a class="idt-heading submenu-heading show-for-medium" style="padding-left: 12px"> Load Certified Luminaire</a>
      </div>
      <div class="grid-x grid-padding-x">
        <div class="small-1 medium-2 large-3 cell"></div>
        <div class="small-10 medium-8 large-6 cell container">
          <div class="grid-y grid-padding-y">
            <div class="small-12 cell">
            <input class="hollow button" type="file" id="fileinput" onchange="loadLcmApp.loadfile(this.files)">
            </div>
            <div class="small-12 float-right">
              <button onclick="loadLcmApp.sendlcm()" class="primary button">Load Luminaires</button>
            </div>
            <div class="small-12">
              <div class="success callout loadlcm-success" aria-live="assertive" style="display: none;">
                <p>Luminaires Successfully loaded</p>
              </div>
            </div>
            <div class="small-12">
              <div class="alert callout loadlcm-fail" aria-live="assertive" style="display: none;">
                <p class="fi-alert"></p>
              </div>
            </div>
          </div>
        </div>
        <div class="small-1 medium-2 large-3 cell"></div>
      </div>
    </div>`;
  }
}