/*global idt_ice _config*/

var idt_ice = window.idt_ice || {};
idt_ice.map = idt_ice.map || {};
idt_ice.lampsDetails = idt_ice.lampsDetails || [];
// var authorizationToken;

function getAuthToken(){
  return str(authorizationToken);
}

(function iceScopeWrapper($) {
  $(async function onDocReady() {
    // await prepWaitCanvas();
    var authToken;
  await idt_ice.authToken.then(function setAuthToken(token) {
    if (token) {
      authToken = token;
    } else {
      // prepSigninCanvas();
      route("signin");
    }
  }).catch(function handleTokenError(error) {
    console.log(error);
    // prepSigninCanvas();
    route("signin");
  });
    await idt_ice.authToken.then(async function updateAuthMessage(token) {
      if (token) {
        await displayUpdate("console",'You are authenticated.');
        // Takes care of landing page when cookie is set.
        let reload = await Cookies.get('ice_page');
        route(reload);
      }
    });
    idleTimer();
  });
}(jQuery));

function idleTimer() {
  var t;
  window.onmousemove = resetTimer; // catches mouse movements
  window.onmousedown = resetTimer; // catches mouse movements
  window.onclick = resetTimer;     // catches mouse clicks
  window.onscroll = resetTimer;    // catches scrolling
  window.onkeypress = resetTimer;  //catches keyboard actions

 function reload() {
        window.location = self.location.href;  //Reloads the current page
 }

 function logout(){
  route("signin");
 }

 async function resetTimer() {
      await clearTimeout(t);
      t = setTimeout(logout, 900000);  // time is in milliseconds (1000 is 1 second)
      // await clearTimeout(t)
      // t= setTimeout(reload, 1200000);  // time is in milliseconds (1000 is 1 second)
      await clearTimeout(t);
  }
}
