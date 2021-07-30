let validateAppUI = {
    canvas: function(){
        return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
        <div id="sub-bar" class="top-bar">
          <div class="top-bar-left">
            <a><img class="menu-logo" alt="lamp"
              src="images/validate_app.png"></a>
          </div>
          <a class="idt-heading submenu-heading show-for-medium">Validate App</a>
        </div>
        <div class="grid-y grid-padding-y">
            <div class="small-4 cell"></div>
            <div class="grid-x grid-padding-x">
                <div class="cell small-6"><h4>Please scan this QR code with the IDT ICE App</h4></div>
                <div id="qrcode" class="cell small-6" Style="padding-left: 5px"></div>
            </div>
        </div>
      </div>`;
    }
}