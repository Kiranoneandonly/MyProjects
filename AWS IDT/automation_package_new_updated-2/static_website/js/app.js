$(document).foundation()

let _lamps;
let _groups;
var _debug= false;

function timeConverter(UNIX_timestamp) {
  var a = new Date(UNIX_timestamp * 1000);
  var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var year = a.getFullYear();
  var month = months[a.getMonth()];
  var date = a.getDate();
  var hour = a.getHours();
  var min = a.getMinutes();
  var sec = a.getSeconds();
  var mdate = date + ' ' + month + ' ' + year;
  return mdate;
}

function getLampList() {
  if(_lamps==undefined || _lamps==0){
    _lamps = getLamps();
    return _lamps;
  }else{
    return _lamps;
  }
}

function getGroupList(){
  if(_groups==undefined || _groups==0){
    _groups = getGroups();
    return _groups;
  }
  return _groups;
}


function refreshLampList(){
  _lamps = getLamps();
  return _lamps;
}

function refreshGroupList(){
  _groups = getGroups();
  return _groups;
}

function prepSigninCanvas() {
  $("#ice-content").replaceWith(getSigninCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-signin').foundation('open')
  });
  $('#signinForm').on("submit", handleSignin);
  $(".signin-alert").css({
    'display': 'none'
  });
}

async function signout() {
  idt_ice.signOut();
  prepSigninCanvas();
  if(_debug){
    console.log("User signed out!");
  }
}

function prepRegisterCanvas() {
  $("#ice-content").replaceWith(getRegisteredCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-register').foundation('open')
  });
  $('#registrationForm').on("submit", handleRegister);
  $(".register-alert").css({
    'display': 'none'
  });
}


function prepVerifyCanvas() {
  $("#ice-content").replaceWith(getVerifyCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-verify').foundation('open')
  });
  $('#verifyForm').on("submit", handleVerify);
  $(".verify-alert").css({
    'display': 'none'
  });
}

function prepChangePasswordCanvas() {
  $("#ice-content").replaceWith(getChangePasswordCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-changePassword').foundation('open')
  });
  $('#changePasswordForm').on("submit", handleChangePassword);
  $(".changePassword-alert").css({
    'display': 'none'
  });
  $(".changePassword-success-callout").css({
    'display': 'none'
  })
}

function prepForgotPasswordCanvas() {
  $("#ice-content").replaceWith(getForgotPasswordCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-forgotPassword').foundation('open')
  });
  $('#forgotPasswordForm').on("submit", handleForgotPassword);
  $(".forgotPassword-alert").css({
    'display': 'none'
  });
  $(".forgotPassword-success-callout").css({
    'display': 'none'
  })
}

function prepChangeForgotPasswordCanvas() {
  $("#ice-content").replaceWith(getchangeForgotPasswordCanvas());
  $("#ice-content").foundation();
  $(document).ready(function () {
    $('#model-changeForgotPassword').foundation('open');
  });
  $('#changeForgetPasswordForm').on("submit", handleChangeForgotPassword);
  $(".changePassword-alert").css({
    'display': 'none'
  });
  $(".changePassword-success-callout").css({
    'display': 'none'
  })
}

function displayUpdate(location, message, type) {
  if(_debug){
    if ("console" === location) {
      console.log(message);
    }
  }
  if("notification"===location){
    console.log("Iam reaching here atleast");
    $("#right-side-notification").replaceWith(`<div id="right-side-notification">
      </div>
      <div class=" ${type?type:""} callout" data-closable style="display: block;">
        <p>${message}</p>
        <button class="close-button" aria-label="Dismiss alert" type="button" data-close>
            <span aria-hidden="true">&times;</span>
        </button>
      </div>`);
  }
}


function onSpinner(){
  document.getElementById("css-spinner").style.display = "block";
}

function offSpinner(){
  document.getElementById("css-spinner").style.display = "none";
}

$(document).keydown(function(e){
  var checkWebkitandIE=(e.which==26 ? 1 : 0);
  var checkMoz=(e.which==73 && e.altKey ? 1 : 0);
  if (checkWebkitandIE || checkMoz){
    if(_debug){
      _debug = false;
      console.log("Debug mode OFF");
    }else{
      _debug = true;
      console.log("Debug mode ON")
    }
  };
});