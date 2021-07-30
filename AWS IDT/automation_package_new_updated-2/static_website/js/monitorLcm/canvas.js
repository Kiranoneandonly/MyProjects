let monitorLCMUI = {
canvas: function(mapUrl){
    return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
    <div id="sub-bar" class="top-bar">
        <div class="top-bar-left">
            <a><img class="menu-logo" alt="lamp"
              src="images/monitor.png"></a>
        </div>
        <a class="idt-heading submenu-heading show-for-medium">Monitor Luminaire</a>
    </div>
    <div id="map"></div>
    <p id="paragraph"></p>
    <script>
        function initMap() {
            getCoordinates();
            let script = document.createElement('script');
            document.getElementsByTagName('head')[0].appendChild(script);
        }
    </script>
    <script async defer
        src="${mapUrl}">
    </script>
  </div>`;
  }
}