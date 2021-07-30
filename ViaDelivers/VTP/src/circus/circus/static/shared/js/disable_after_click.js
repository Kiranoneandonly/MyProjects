"use strict";

$(document).ready(function () {
    var elements_to_disable = $(".disable_after_click");
    elements_to_disable.click(function (e) {
        var button = $(e.target), icon;
        if (button.hasClass("disabled")) {
            e.preventDefault();
            e.stopPropagation();
        } else {
            button.css("cursor", "wait");
            icon = button.find(".fa");
            if (!icon.length) {
                icon = $("<i></i> ", {
                    'class': 'fa fa-fw'
                });
                button.append(icon);
            }
            icon.addClass("fa-spinner fa-spin");
            button.addClass("disabled");
            button.attr("title", "Loading…");
        }
    });
});