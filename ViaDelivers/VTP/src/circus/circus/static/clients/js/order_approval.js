"use strict";

/* global INITIAL_PROJECT_SPEED */

$(document).ready(function(){
    function set_selected($sel, state){
        $sel.each(function(){
            if(state){
                $(this).addClass('selected');
            } else {
                $(this).removeClass('selected');
            }
        });
    }
    var inspect;

    $("input:radio[name='payment_method']").click(function() {
        $('.desc').hide();
        $('#' + $("input:radio[name='payment_method']:checked").val()).show();
    });

    $('input:radio[name="project_speed"]').click(function(){
        var value = $(this).val();
        var standard = $(this).parents('table.estimate-table').find('tbody').find('.standard');
        var express = $(this).parents('table.estimate-table').find('tbody').find('.express');
        set_selected(standard, value=='standard');
        set_selected(express, value=='express');
    });

    $('input:radio[value=' + INITIAL_PROJECT_SPEED + ']').trigger('click');
});
