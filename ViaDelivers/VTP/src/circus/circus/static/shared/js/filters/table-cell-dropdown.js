"use strict";

$(function() {
    /* Target Locale Expand
     * ***********************/
    $(".table-cell-dropdown-toggle i.fa-caret-down, .table-cell-dropdown-toggle i.fa-caret-up").click(function(e) {
        var self = $(this);
        if (self.hasClass('fa-caret-down')) {
            self.switchClass('fa-caret-down', 'fa-caret-up');
            self.parent().parent().find('.table-cell-additional-item').css('display', 'block');
        } else {
            self.switchClass('fa-caret-up', 'fa-caret-down');
            self.parent().parent().find('.table-cell-additional-item').css('display', 'none');
        }
    });
});
