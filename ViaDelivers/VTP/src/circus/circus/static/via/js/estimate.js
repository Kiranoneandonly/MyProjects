$(function(){
    "use strict";

    $('.upload-btn').click(function(e) {
        var lightbox_id = $(this).data('lightbox');
        $('#' + lightbox_id).lightbox_me({
            centered: true
        });
        e.preventDefault();
    });
});
