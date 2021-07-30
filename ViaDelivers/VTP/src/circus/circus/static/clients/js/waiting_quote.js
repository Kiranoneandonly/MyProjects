"use strict";

/* global msg_settings, settings */

$(function() {
    var time = 0,
        update_interval,
        MAX_WIDTH = 480,
        analyzing_messages = ['Initializing'],
        analysis_message = $("#analysis_step .message"),
        progressbar_value = $( "#progressbar .progressbar-value");

    /* FUNCTIONS */


    var get_messages = function(settings) {
        $.ajax({
            type: 'GET',
            url: settings.url,
            cache: false,
            dataType: 'json',
            success: function(response) {
                analyzing_messages = response;
            }
        });
    };

    var get_analysis_message = function() {
        var choice = Math.floor(Math.random() * analyzing_messages.length);
        return analyzing_messages[choice];
    };

    var check_analysis_status = function(settings) {
        $.ajax({
            type: 'GET',
            url: settings.check_url,
            cache: false,
            dataType: 'json',
            success: function(response) {
                if (response.complete) {
                    complete_analysis(settings.auto_quote_url);
                } else if (response.force_manual_estimate) {
                    window.location.assign(settings.manual_quote_url);
                } else {
                    // check again in another second
                    setTimeout(function() {
                        check_analysis_status(settings);
                    }, 1000);
                }
            }
        });
    };

    var progressbar_update = function() {
        var width = progressbar_value.width();

        var offset = 18;
        if (time < 10) {
            offset = 18;
        } else if (time >= 10 && time < 20) {
            offset = 12;
        } else if (time >= 20 && time < 30) {
            offset = 6;
        } else if (time >= 30) {
            offset = 4;
        }

        var new_width = width + offset;
        if (new_width >= MAX_WIDTH) {
            new_width = MAX_WIDTH;
            clearInterval(update_interval);
        }

        progressbar_value.animate({
            'width': new_width  + 'px'
        },{
            'duration': 980,
            'easing': 'linear',
            'queue': false
        });

        if (time % 2)
           analysis_message.text(get_analysis_message());
        time += 1;
    };

    var complete_analysis = function(redirect_url) {
        clearInterval(update_interval);
        progressbar_value.animate({
            'width': MAX_WIDTH  + 'px'
        },{
            'duration': 1000,
            'easing': 'linear',
            'queue': false
        });
        setTimeout(function() {
            analysis_message.text("Finishing Up");
            window.location.assign(redirect_url);
        }, 1000);
    };

    /* INVOCATIONS */

    analyzing_messages = get_messages(msg_settings);
    check_analysis_status(settings);
    update_interval = setInterval(progressbar_update, 1000);
});
