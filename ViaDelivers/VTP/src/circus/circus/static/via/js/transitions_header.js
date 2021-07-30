$(function(){
    "use strict";

    $('.confirm_submit').click(function (e) {
        var confirm_msg, label = $(this).text();
        var $form = $(this).closest("form");

        confirm_msg = label + ": Are you sure?";

        if (window.confirm(confirm_msg)) {
            $form.submit();
        }
    });
});
