/*
  Updates Any Accordion Icon.
  Just include:
    <span class="accordion-icon">+</span>
  To your accordion-toggle!
*/

"use strict";

$(function() {
    var accordion_body = $(".accordion-body");
    accordion_body.on("show",function(event){
        var accordion_toggle_icon = $(this).parent('.accordion-group').find('.accordion-icon');
        accordion_toggle_icon.text('-');
    });
    accordion_body.on("hide",function(event){
        var accordion_toggle_icon = $(this).parent('.accordion-group').find('.accordion-icon');
        accordion_toggle_icon.text('+');
    });
});
