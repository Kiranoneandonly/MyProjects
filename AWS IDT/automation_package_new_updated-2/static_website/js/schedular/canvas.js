let schedularUI = {
    canvas: function () {
        return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content >
        <div id="sub-bar" class="top-bar" style="margin-bottom: 50px;">
          <div class="top-bar-left">
            <a><img class="menu-logo" alt="lamp"
              src="images/schedular.png"></a>
          </div>
          <a class="idt-heading submenu-heading show-for-medium" style="padding-left: 10px;">Scheduler</a>
        </div>
        <div style="float:left;">
        <section>
        <div id="sliders">
        </div>
      </section>
      <hr style="clear:both; visibility: hidden;">
          <label>Day profile
            <select style="width:150px;" id="daysProfile" onchange="reinitSlider()">
  
            </select>
          </label>
        </div>
  
        <div style="float:left;">
          <form>
            <div class="grid-x grid-padding-x">
              <div class="small-5 cell">
                <label for="dayProfileName" class="text-right">Day Profile Name:</label>
              </div>
              <div class="small-6 cell">
                <input type="text" id="dayProfileName">
              </div>
              <div class="small-2 cell">
                <button type="button" class="success button" onclick="saveDimValues()">Save</button>
              </div>
              <div class="small-2 cell">
                <button type="button" class="alert button">Delete</button>
              </div>
            </div>
          </form>
  
        </div>
        <hr style="clear:both; visibility: hidden;">
        <div>
          <label>Week profile
            <select style="width:150px;" id="weekProfile" onchange="reinitDays()">
            </select>
          </label>
        </div>
        <hr style="clear:both; visibility: hidden;">
  
        <div>
  
          <div style="float:left;">
            <label>Mon
              <select style="width:150px;" id="weekday0">
              </select>
            </label>
          </div>
  
          <div style="float:left;">
            <label>Tue
              <select style="width:150px;" id="weekday1">
              </select>
            </label>
          </div>
  
          <div style="float:left;">
            <label>Wed
              <select style="width:150px;" id="weekday2">
              </select>
            </label>
          </div>
  
          <div style="float:left;">
            <label>Thu
              <select style="width:150px;" id="weekday3">
              </select>
            </label>
          </div>
          <div style="float:left;">
            <label>Fri
              <select style="width:150px;" id="weekday4">
              </select>
            </label>
          </div>
          <div style="float:left;">
            <label>Sat
              <select style="width:150px;" id="weekday5">
              </select>
            </label>
          </div>
          <div style="float:left;">
            <label>Sun
              <select style="width:150px;" id="weekday6">
              </select>
            </label>
          </div>
  
  
  
  
        </div>
  
        <hr style="clear:both; visibility: hidden;">
        <div style="float:left;">
          <form>
            <div class="grid-x grid-padding-x">
              <div class="small-5 cell">
                <label for="weekProfileName" class="text-left">Week Profile Name:</label>
              </div>
              <div class="small-6 cell">
                <input type="text" id="weekProfileName" class="text-left">
              </div>
              <div class="small-2 cell">
                <button type="button" class="success button" onclick="saveWeekValues()">Save</button>
              </div>
              <div class="small-2 cell">
                <button type="button" class="alert button">Delete</button>
              </div>
            </div>
          </form>
  
        </div>
  
      </div>`}
}