/*global idt_ice _config AmazonCognitoIdentity AWSCognito*/

var idt_ice = window.idt_ice || {};
var handleSignin;
var handleRegister;
var handleVerify;
var handleChangePassword;
var handleForgotPassword;
var handleChangeForgotPassword;
var resendVerificationEmail;

(function scopeWrapper($) {

    var poolData = {
        UserPoolId: _config.cognito.userPoolId,
        ClientId: _config.cognito.userPoolClientId
    };

    // AWS.config.region = _config.cognito.region;
    // AWS.config.UserPoolId = _config.cognito.userPoolId;
    // AWS.config.ClientId = _config.cognito.userPoolClientId;
    // var cognitoidentityserviceprovider = new AWS.CognitoIdentityServiceProvider();

    var userPool;
    var cognitoUser;

    if (!(_config.cognito.userPoolId &&
          _config.cognito.userPoolClientId &&
          _config.cognito.region)) {
        $('#noCognitoMessage').show();
        return;
    }

    userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);
    // cognitoIdentity = new AWS.CognitoIdentity();
    // userPool = new cognitoIdentity.CognitoUserPool(poolData);

    if (typeof AWSCognito !== 'undefined') {
        AWSCognito.config.region = _config.cognito.region;
    }

    idt_ice.signOut = function signOut() {
        if(userPool.getCurrentUser()){
            userPool.getCurrentUser().signOut();
        }
    };


    idt_ice.authToken = new Promise(function fetchCurrentAuthToken(resolve, reject) {
        cognitoUser = userPool.getCurrentUser();

        if (cognitoUser) {
            cognitoUser.getSession(function sessionCallback(err, session) {
                if (err) {
                    reject(err);
                } else if (!session.isValid()) {
                    resolve(null);
                } else {
                    resolve(session.getIdToken().getJwtToken());
                }
            });
        } else {
            resolve(null);
        }
    });

    /*
     * Cognito User Pool functions
     */

    function register(email, password, onSuccess, onFailure) {
        var dataEmail = {
            Name: 'email',
            Value: email
        };
        var attributeEmail = new AmazonCognitoIdentity.CognitoUserAttribute(dataEmail);

        userPool.signUp(toUsername(email), password, [attributeEmail], null,
            function signUpCallback(err, result) {
                if (!err) {
                    onSuccess(result);
                } else {
                    onFailure(err);
                }
            }
        );
    }

    function signin(email, password, onSuccess, onFailure) {
        var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails({
            Username: toUsername(email),
            Password: password
        });

        var cognitoUser = createCognitoUser(email);
        cognitoUser.authenticateUser(authenticationDetails, {
            onSuccess: onSuccess,
            onFailure: onFailure
        });
    }

    function verify(email, code, onSuccess, onFailure) {
        createCognitoUser(email).confirmRegistration(code, true, function confirmCallback(err, result) {
            if (!err) {
                onSuccess(result);
            } else {
                onFailure(err);
            }
        });
    }

    function createCognitoUser(email) {
        return new AmazonCognitoIdentity.CognitoUser({
            Username: toUsername(email),
            Pool: userPool
        });
    }

    function toUsername(email) {
        return email.replace('@', '-at-');
    }

    /*
     *  Event Handlers
     */

    $(function onDocReady() {
        $('#signinForm').submit(handleSignin);
        $('#registrationForm').submit(handleRegister);
        $('#changePasswordForm').submit(handleChangePassword);
        $('#verifyForm').submit(handleVerify);
        $('#forgotPasswordForm').submit(handleForgotPassword);
        $('#changeForgetPasswordForm').submit(handleChangeForgotPassword);
    });

    

    handleSignin = function (event) {
        var email = $('#emailInputSignin').val();
        var password =  $('#passwordInputSignin').val();
        $(".signin-alert").css({'display': 'none'});
        console.log(email);
        event.preventDefault();
        if(email && password){
        signin(email, password,
            async function signinSuccess() {
                console.log('Successfully Logged In');
                idt_ice.authToken = new Promise(function fetchCurrentAuthToken(resolve, reject) {
                    cognitoUser =  userPool.getCurrentUser();
            
                    if (cognitoUser) {
                        cognitoUser.getSession(function sessionCallback(err, session) {
                            if (err) {
                                reject(err);
                            } else if (!session.isValid()) {
                                resolve(null);
                            } else {
                                resolve(session.getIdToken().getJwtToken());
                            }
                        });
                    } else {
                        resolve(null);
                    }
                });
                let reload = await Cookies.get('ice_page');
                await route(reload);
            },
            function signinError(err) {
                console.log(err);
                $(".fi-alert").text("Unable to signin. Incorrect username or password");
                $(".signin-alert").css({'display': 'block'});
            }
        );
        }
        else{

        }
    }

    const delay = ms => new Promise(res => setTimeout(res, ms));

    handleRegister = function(event) {
        var email = $('#emailInputRegister').val();
        var password = $('#passwordInputRegister').val();
        var password2 = $('#password2InputRegister').val();
        $(".register-alert").css({'display': 'none'});

        var onSuccess = function registerSuccess(result) {
            var cognitoUser = result.user;
            console.log('user name is ' + cognitoUser.getUsername());
            var confirmation = ('Registration successful. Please check your email inbox or spam folder for your verification code.');
            if (confirmation) {
                // waitandforward(".register-success-callout",registerToVerify);
                waitandroute(".register-success-callout","verify");
            }
        };
        var onFailure = function registerFailure(err) {
            $(".fi-alert").text(err);
            $(".register-alert").css({'display': 'block'});
        };
        event.preventDefault();

        if (password === password2) {
            register(email, password, onSuccess, onFailure);
        } else {
            $(".fi-alert").text("Password doesn't Match");
            $(".register-alert").css({'display': 'block'});
        }
    }

    async function waitandforward(reveal,redirectMethod){
        await $(reveal).css({'display': 'block'});
        await delay(5000);
        await redirectMethod();
    }

    async function waitandroute(reveal,page){
        await $(reveal).css({'display': 'block'});
        await delay(5000);
        await route(page);
    }

    handleVerify = function (event) {
        var email = $('#emailInputVerify').val();
        var code = $('#codeInputVerify').val();
        event.preventDefault();
        verify(email, code,
            function verifySuccess(result) {
                console.log('call result: ' + result);
                console.log('Successfully verified');
                // waitandforward(".verify-success-callout",verifyToSignin);
                waitandroute(".verify-success-callout","signin");
            },
            function verifyError(err) {
                $(".fi-alert").text(err);
                $(".verify-alert").css({'display': 'block'});
            }
        );
    }

    handleChangePassword = function (event) {
        event.preventDefault();
        $(".changePassword-alert").css({'display': 'none'});
        let oldP = $('#oldPassword').val();
        let newP1 = $('#newPassword1').val();
        let newP2 = $('#newPassword2').val();
        let onSuccess = function(){
            $(".changePassword-success-callout").show();
        }
        let onFailure = function(err){
            $(".fi-alert").text(err);
            $(".changePassword-alert").css({'display': 'block'});
        }
        if (newP1 === newP2) {
            sendChangePasswordRequest(oldP, newP1, onSuccess, onFailure);
        }else{
            $(".fi-alert").text("New Password doesn't Match");
            $(".changePassword-alert").css({'display': 'block'});
        }
    }

    sendChangePasswordRequest = async function(oldPassword, newPassword, onSuccess, onFailure){
        cognitoUser.changePassword(oldPassword, newPassword, function(err, data) {
            if (err){
                console.log(err, err.stack); // an error occurred 
                onFailure(err);
            } 
            else {
                console.log(data);           // successful response
                onSuccess();
            }
          });
    }


    handleForgotPassword = async function(){
        event.preventDefault();
        let vemail = document.getElementById("verifiedEmailInput").value;
        let username = toUsername(vemail);

        var userData = {
            Username : username,
            Pool : userPool,
        };

        let cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);
        
        cognitoUser.forgotPassword({
            onSuccess: function (result) {
                waitandroute(".forgotPassword-success-callout","signin");
            },
            onFailure: function(err) {
                $(".fi-alert").text(err);
                $(".forgotPassword-alert").css({'display': 'block'});
                console.log(err);
            },
            inputVerificationCode() {
                forgotPasswordforgotPasswordInstance = this;
                forgotPasswordUser = cognitoUser;
                waitandroute('.forgotPassword-success-callout','changeForgotPassword');
            }
        });
        
    }

    let forgotPasswordUser;
    let forgotPasswordInstance;

    handleChangeForgotPassword = async function(){
        event.preventDefault();
        $(".forgotPassword-success-callout").hide();
        $(".forgotPassword-alert").css({'display': 'none'});
        let verificationCode = document.getElementById("verificationCode").value;
        let newPassword1 = $('#newPassword1').val();
        let newPassword2 = $('#newPassword2').val();
        if (newPassword1 === newPassword2) {
            forgotPasswordUser.confirmPassword(verificationCode, newPassword1, forgotPasswordInstance);
        }else{
            $(".fi-alert").text("New Password doesn't Match");
            $(".changePassword-alert").css({'display': 'block'});
        }
    }

    resendVerificationEmail = function(){
        event.preventDefault();
        let vemail = document.getElementById("nonVerifiedEmail").value;
        let username = toUsername(vemail);
        $(".verificationEmailSent-fail").hide();
        $(".verificationEmailSent-success").hide();
        if(vemail===""){
            $(".vef-alert").text("Please enter email");
            $(".verificationEmailSent-fail").show();
            return;
        }

        var userData = {
            Username : username,
            Pool : userPool,
        };

        let cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

        onSuccess = function(){
            $(".verificationEmailSent-success").show();
        };
        onFilure = function(err){
            console.log(err);
            $(".vef-alert").text(err);
            $(".verificationEmailSent-fail").show();
        };

        cognitoUser.resendConfirmationCode(function(err, result) {
            if (err) {
                onFilure(err);
                return;
            }
            onSuccess();
        });
    }

}(jQuery));
