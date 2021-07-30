let registerlcmUI = {
    canvas: function(){
        return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
        <div id="sub-bar" class="top-bar">
          <div class="top-bar-left">
            <a><img class="menu-logo" alt="lamp"
              src="images/lamp_add.png"></a>
          </div>
          <a class="idt-heading submenu-heading show-for-medium" style="padding-left: 12px">  Register Luminaire</a>
        </div>
        <div class="grid-y grid-padding-y">
            <div class="small-4 cell"></div>
            <div class="grid-x grid-padding-x">
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-10 medium-8 large-4 cell container align-center">
                    <div class="cell responsive-embed" style="display: none;">
                        <video id="video"
                            style="border: 1px solid gray; box-shadow: 0 2px 5px 0 rgba(0,0,0,.16), 0 2px 10px 0 rgba(0,0,0,.12);"
                            autoplay="true" muted="true" playsinline="true" autofocus="true"></video>
                    </div>
                    <div class="cell">
                        <button onclick="startQRScanner()" class="button small" type="button" id="startButton">Scan</button>
                        <button onclick="resetQRScanner()" class="button small float-right alert" type="button"
                            id="resetButton">Reset</button>
                        <button class="button small" type="button" onclick="getLocation()">Refresh GPS
                            Location</button>
                    </div>
                </div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-10 medium-8 large-4 cell" id="sourceSelectPanel">
                    <label for="sourceSelect">Change video source:</label>
                    <select id="sourceSelect">
                    </select>
                </div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-10 medium-8 large-4 cell">
                    <form data-abide novalidate>
                        <div data-abide-error class="alert callout form-error-callout" style="display: none;">
                            <p><i class="fi-alert"> There are some errors in your form.</i></p>
                        </div>
                        <label>Luminaire ID:
                            <input id="luminaire" type="text" aria-errormessage="luminaireError1" required>
                            <span class="form-error" id="luminaireError1" style="display: none;">
                                Please fill the Luminaire Id.
                            </span>
                        </label>
                        <label>Luminaire IP:
                            <input id="luminaire-ip" type="text" aria-errormessage="luminaireError1" required>
                            <span class="form-error" id="luminaire-ipError1" style="display: none;">
                                Please fill the Luminaire IP Address.
                            </span>
                        </label>
                        <label>Longitude:
                            <input id="longitude" type="number" aria-errormessage="longitudeError1" required>
                            <span class="form-error" id="longitudeError1" style="display: none;">
                                Longitude is Missing, it is a required field.
                            </span>
                        </label>
                        <label>Latitude:
                            <input id="latitude" type="number" aria-errormessage="latitudeError1" required>
                            <span class="form-error" id="latitudeError1" style="display: none;">
                                Latitude is Missing or non numeric values
                            </span>
                        </label>
                        <label>Hub ID:
                            <input id="hubID" type="text" aria-errormessage="hubIDError1" required>
                            <span class="form-error" id="hubIDError1" style="display: none;">
                                Please fill the Hub Id. It is a required field.
                            </span>
                        </label>
                        <button class="button alert float-left" onclick="resetRegisterLampForm()" id="registerReset"
                            type="button">Reset Form</button>
                        <button class="button float-right" onclick="registerLamp()" id="register"
                            type="button">Submit</button>
                    </form>
                </div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-1 medium-2 large-4 cell"></div>
                <div class="small-10 medium-8 large-4 cell">
                    <div class="callout success register-success" data-closable style="display: none;">
                        <h5>Success!</h5>
                        <p>The lamp has been successfully commissioned</p>
                        <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div id="register-failure" class="callout alert" data-closable style="display: none;">
                        <h5>Failure!</h5>
                        <p id="register-error-content"></p>
                        <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
      </div>`;
      }
}