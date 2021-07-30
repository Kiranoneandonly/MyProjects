function getSigninCanvas(){
  return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-signin" data-reveal data-options="closeOnClick:false; closeOnEsc:false">
    <div class="grid-x">
      <div class="cell medium-5">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
        </div>
        <div class="cell medium-7">
          <p class="idt-heading model-heading">Sign In</p>
        </div>
      </div>
      <!-- Signin Form -->
      <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
        <h3 style="margin-top: 1em; margin-bottom: 1em ">Please sign in to access the dashboard!</h3>
        <div class="grid-x medium-up-2" style="border-bottom: solid 2px; border-color: #e6e6e6;">
          <section class="form-wrap">
            <div data-abide-error="" class="alert callout signin-alert" aria-live="assertive">
              <p class="fi-alert"></p>
            </div>
            <form id="signinForm"  data-abide novalidate>
              <input type="email" id="emailInputSignin" placeholder="Email" aria-errormessage="emailMissingError" required>
              <input type="password" id="passwordInputSignin" aria-errormessage="passwordMissingError" placeholder="Password" pattern=".*" required>
              <input class="button" type="submit" value="Sign in">
            </form>
          </section>
        </div>
        <span>Not yet registered? <a onclick="route('register')" type="button">Register Here</a></span>
        <span>Registered but not verified? <a onclick="route('verify')" type="button">Verify Here</a></span>
        <span>Forgot Password? <a onclick="route('forgotPassword')" type="button">Click Here</a></span>
      </div>
  </div>
</div>`;
}

function getRegisteredCanvas(){
  return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-register" data-reveal data-options="closeOnClick:false; closeOnEsc:false">
    <div class="grid-x align-center">
      <div class="cell medium-5">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
      </div>
      <div class="cell medium-7">
        <p class="idt-heading model-heading">Register</p>
      </div>
    </div>
    <!-- Register Form -->
    <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
      <div class="callout success register-success-callout">
        <h5>You have been successfully registered</h5>
        <p>Please check your email inbox or spam folder for your verification code.</p>
        <a onlick="route('verify')" type="button">If you are not able to redirect in 10 secs please click on me</a>
      </div>
          <h3 style="margin-top: 1em">Please enter registration details</h3>
          <div class="grid-x medium-up-2 pre-signin-form" style="border-bottom: solid 2px; border-color: #e6e6e6;">
              <section class="form-wrap">
                  <form id="registrationForm">
                    <div data-abide-error="" class="alert callout register-alert" aria-live="assertive">
                      <p class="fi-alert"></p>
                    </div>
                    <input type="email" id="emailInputRegister" placeholder="Email"  required>
                    <input type="password" id="passwordInputRegister" placeholder="Password" pattern=".*" required>
                    <input type="password" id="password2InputRegister" placeholder="Confirm Password" pattern=".*" required>
                    <input class="button" type="submit" value="Submit">
                  </form>
              </section>
          </div>
          <span>Already Registered? <a  onclick="route('signin')" type="button">Signin Here</a></span>
          <span>Registered but not verified? <a  onclick="route('verify')" type="button">Verify Here</a></span>
      </div>
  </div>
</div>`;
}

function getVerifyCanvas(){
  return `
<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-verify" data-reveal data-options="closeOnClick:false; closeOnEsc:false" style="border-color: #1779BA">
    <div class="grid-x align-center">
      <div class="cell medium-5">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
      </div>
      <div class="cell medium-7">
        <p class="idt-heading model-heading">Verify</p>
      </div>
    </div>
    <!-- Verify Registration Form -->
    <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
      <div class="callout success verify-success-callout">
        <h5>You have been successfully verified</h5>
        <p>Now you can login to acces the dashboard.</p>
        <a onlick="route('signin')" type="button">If you are not able to redirect in 10 secs please click on me</a>
      </div>
      <h3 style="margin-top: 1em">Please verify your email address</h3>
      <div class="grid-x medium-up-2" style="border-bottom: solid 2px; border-color: #e6e6e6;">
        <section class="form-wrap">
          <form id="verifyForm">
            <div data-abide-error="" class="alert callout verify-alert" aria-live="assertive">
              <p class="fi-alert"></p>
            </div>
            <input type="email" id="emailInputVerify" placeholder="Email" required>
            <input type="text" id="codeInputVerify" placeholder="Verification Code" pattern=".*" required>
            <input class="button" type="submit" value="Verify">
          </form>
        </section>
      </div>
      <h5>Resend the verification code email</h5>
      <div class="grid-x small-up-1 align-right" style="border-bottom: solid 2px; border-color: #e6e6e6; padding-top: 12px; max-width: 370px;">
          <div class="cell">
            <input type="email" id="nonVerifiedEmail" placeholder="Email" required>
          </div>
          <div cladd="cell">
            <button class="primary button" onclick="resendVerificationEmail()">Send</button>
          </div>
          <div class="callout success verificationEmailSent-success cell" style="display: none">
            <h5>Verification email sent</h5>
            <p>Please check your email.</p>
          </div>
          <div class="callout alert verificationEmailSent-fail cell" style="display: none">
            <h5>Request Couldn't be processed</h5>
            <p class="vef-alert"></p>
          </div>
      </div>
      <span>Already verified? <a  onclick="route('signin')" type="button">Signin Here</a></span>
      <span>Not yet registered? <a  onclick="route('register')" type="button">Register Here</a></span>
    </div>
  </div>
</div>`;
}

function getChangePasswordCanvas(){
  return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-changePassword" data-reveal data-options="closeOnClick:false; closeOnEsc:false" style="border-color: #1779BA">
    <div class="grid-x align-center">
      <div class="cell medium-4">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
      </div>
        <div class="cell medium-8">
          <p class="idt-heading model-heading">Change Password</p>
        </div>
      </div>
      <!-- Change Pssword Form -->
      <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
      <div class="callout success changePassword-success-callout">
        <h5>Your Password has been successfully changed</h5>
      </div>
        <h3 style="margin-top: 1em">Please enter your old password and the new password</h3>
        <div class="grid-x medium-up-2" style="border-bottom: solid 2px; border-color: #e6e6e6;">
          <section class="form-wrap">
            <form id="changePasswordForm">
              <div data-abide-error="" class="alert callout changePassword-alert" aria-live="assertive">
                <p class="fi-alert"></p>
              </div>
              <input type="password" id="oldPassword" placeholder="Old Password" required>
              <input type="password" id="newPassword1" placeholder="New Password" pattern=".*" required>
              <input type="password" id="newPassword2" placeholder="Confirm New Password" pattern=".*" data-equalto="newPassword1" required>
              <button class="button" type="submit">Change Password</button>
            </form>
          </section>
        </div>
        <span>Wanna Go Back? <a  onclick="route('group')" type="button">Cick here</a></span>
      </div>
  </div>
</div>`;
}

function getForgotPasswordCanvas(){
  return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-forgotPassword" data-reveal data-options="closeOnClick:false; closeOnEsc:false" style="border-color: #1779BA">
    <div class="grid-x align-center">
      <div class="cell medium-5">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
      </div>
        <div class="cell medium-7">
          <p class="idt-heading model-heading">Forgot Password</p>
        </div>
      </div>
      <!-- Forgot Password Form -->
      <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
      <div class="callout success forgotPassword-success-callout">
        <h5>Verification email has been sent to the email address</h5>
        <a onlick="route('changeForgotPassword')" type="button">If you are not able to redirect in 10 secs please click on me</a>
      </div>
        <h3 style="margin-top: 1em">Enter the verified email address</h3>
        <div class="grid-x medium-up-2" style="border-bottom: solid 2px; border-color: #e6e6e6;">
          <section class="form-wrap">
            <form id="forgotPasswordForm">
              <div data-abide-error="" class="alert callout forgotPassword-alert" aria-live="assertive">
                <p class="fi-alert"></p>
              </div>
              <input type="email" id="verifiedEmailInput" placeholder="Email" required>
              <button class="button" type="submit">Submit</button>
            </form>
          </section>
        </div>
        <span>Want to signin? <a  onclick="route('signin')" type="button">Signin Here</a></span>
      </div>
  </div>
</div>`;
}

function getchangeForgotPasswordCanvas(){
  return `<div id="ice-content" class="off-canvas-content" data-off-canvas-content>
  <div class="large reveal" id="model-changeForgotPassword" data-reveal data-options="closeOnClick:false; closeOnEsc:false" style="border-color: #1779BA">
    <div class="grid-x align-center">
      <div class="cell medium-4">
        <a href="https://www.idt.com/"><img class="menu-logo"
        alt="IDT - Integrated device Tachnology"
        src="images/new_idt.png"></a><br /><br />
      </div>
        <div class="cell medium-8">
          <p class="idt-heading model-heading">Change Password</p>
        </div>
      </div>
      <!-- Change Password Form -->
      <div class="grid-y grid-padding-y align-middle" style="border-top: solid 2px; border-color: #e6e6e6;">
      <div class="callout success forgotPassword-success-callout">
        <h5>Your Password has been successfully changed</h5>
      </div>
        <h3 style="margin-top: 1em">Please enter your verification code and the new password</h3>
        <div class="grid-x medium-up-2" style="border-bottom: solid 2px; border-color: #e6e6e6;">
          <section class="form-wrap">
            <form id="changeForgetPasswordForm">
              <div data-abide-error="" class="alert callout forgotPassword-alert" aria-live="assertive">
                <p class="fi-alert"></p>
              </div>
              <input type="text" id="verificationCode" placeholder="Verification Code" required>
              <input type="password" id="newPassword1" placeholder="New Password" pattern=".*" required>
              <input type="password" id="newPassword2" placeholder="Confirm New Password" pattern=".*" data-equalto="newPassword1" required>
              <button class="button" type="submit">Change Password</button>
            </form>
          </section>
        </div>
        <span>Want to signin? <a  onclick="route('signin')" type="button">Signin Here</a></span>
      </div>
  </div>
</div>`;
}