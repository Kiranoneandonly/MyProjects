requirejs.config({
    // By default load any module IDs from js/vendor
    // base vendor has been chosen on purpose due to jquery constraints 
    // Please add the paths in alphabatical order for easy readablity purpose
    baseUrl: 'js/vendor',
    paths: {
        app: '..',
        lcms: '../lcms',
        monitorLcm: '../monitorLcm',
        registerLcm: '../registerLcm',
        registerUser: '../registerUser',
        schedular: '../schedular',
        signin: '../signin',
        validateApp: '../validateApp',
        verify: '../verify',
        groups: '../groups',
        addGroup: "../addGroup",
        loadLcm: "../loadLcm",
    }
});

// Outer files are loaded first then the inner files loaded
// Please check the when do you want the file to be loaded for the website
requirejs(['jquery', 'html5shiv.min', 'app/config', 'app/canvas-display'],
    function ($, html5shiv, config, canvas_display) {
        requirejs(['foundation', 'app/endpoints', 'app/cognito-auth'],
            function (foundation, endpoints, cognito_auth) {
                requirejs(['app/app', 'app/ice-utils', 'app/redirect'],
                    function (app, ice_utils, redirect) {
                        requirejs(['app/ice'],function(ice){});
                    });
            });
    });