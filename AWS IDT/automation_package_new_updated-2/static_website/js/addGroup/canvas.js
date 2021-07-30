addGroupUI = {
  canvas: function(){
    return `
      <div id="ice-content" class="off-canvas-content" data-off-canvas-content>
        <div id="sub-bar" class="top-bar">
          <div class="top-bar-left">
            <a><img class="menu-logo" alt="lamp"
              src="images/register_group_96px.png"></a>
          </div>
          <a class="idt-heading submenu-heading show-for-medium">Add new Group</a>
        </div>
        <div class="grid-x grid-padding-x">
          <div class="small-1 medium-2 large-3 cell"></div>
          <div class="grid-y grid-padding container align-center small-10 medium-8 large-6">
            </br>
            <div>
              <div class="alert callout form-error-callout" data-closable style="display: none;">
                <p><i class="fi-alert"> There are some errors in your form.</i></p>
                <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
              <div class="alert callout submit-error-callout" data-closable style="display: none;">
                <p><i class="fi-alert"> Something Went Wrong, Unable to create new Group.</i></p>
                <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
              <div class="success callout submit-success-callout" data-closable style="display: none;">
                <p><i class="fi-alert"> Group Successfully Created</i></p>
                <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
              <label>Group Name: <a style="color:#cc4b37"><b>Required</b><a>
                <input id="group-name" type="text" aria-errormessage="groupError1" required>
                <span class="form-error" id="groupError1" style="display: none;">
                  Please fill the Group Name with only aplanumeric values. Only allowed characters are a-z, A-Z, 0-9 and underscore(_)
                </span>
                <span class="form-error" id="groupError2" style="display: none;">
                  Group Name already Present.
                </span>
              </label>
              <label>Description:
                <textarea id="group-description" aria-errormessage="group-descError1"></textarea>
                <span class="form-error" id="group-descError1" style="display: none;">
                 Special characters are not allowed. Only space(&#8220; &#8220);, plus(+), minus(-), underscore(_), period(.) are allowed. 
                </span>
              </label>
              <fieldset class="small-12 cell">
                <label>Choose Form Type <img class="side-menu-img" id="generate-form-wait"alt="User" src="images/loading1.gif" style="display: none"></label>
                <input type="radio" name="edit-1radio" value="ip" id="edit-1radio1" checked required><label for="edit-1radio1">IP</label>
                <input type="radio" name="edit-1radio" value="key" id="edit-1radio2" required><label for="edit-1radio2">Serial</label> 
                <button onclick="addGroupApp.populateGroupLcmList()" class="primary button small"><b>Generate</b></button>
              </fieldset>
              <div class="grid-x grid-padding-x">
                <div class="medium-5 cell">
                  <label>Unadded Luminaires
                    <input type="search" class="create-search-unadded" id="search-unadded-lcm" placeholder="Search luminaire">
                    <select multiple id="unadded-lcm">
                    </select>
                  </label>
                </div>
                <div class="medium-2 cell">
                  <div class="show-for-medium" style="padding-top: 60px;"></div>
                  <img onclick="addGroupApp.addLcmInGroup()" class="side-menu-img generate-form-wait" alt="User" src="images/plus_96px.png">
                  <img onclick="addGroupApp.removeLcmInGroup()" class="side-menu-img generate-form-wait" alt="User" src="images/minus_96px.png">
                </div>
                <div class="medium-5 cell">
                  <label>Added Luminaires
                    <input type="search" class="create-search-added" id="search-added-lcm" placeholder="search Luminaire">
                    <select multiple id="added-lcm">
                    </select>
                  </label>
                </div>
              </div>
              <button type="button" onclick="addGroupApp.clearForm()" class="button alert">Clear</button>
              <div class="float-right">
                <button type="button" onclick="addGroupApp.submit()" class="button primary">Submit</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  selectorOption: function(value, displayValue, selected){
    return `<option value="${value}" ${selected}>${displayValue}</option>`;
  }

}