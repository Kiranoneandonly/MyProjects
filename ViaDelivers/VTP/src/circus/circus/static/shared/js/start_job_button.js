"use strict";

$(document).ready(function () {
    var start_job_buttons = $(".start_job_button");
    start_job_buttons.click(function (e) {
        var button = $(e.target), icon;
        if (button.hasClass("disabled")) {
            e.preventDefault();
            e.stopPropagation();
        } else {
            button.css("cursor", "wait");
            icon = button.find(".fa");
            icon.removeClass("fa-plus-circle");
            icon.addClass("fa-spinner fa-spin");
            button.addClass("disabled");
            button.attr("title", "Loading…");
        }
    });
});