"use strict";

$(function() {
    /* Job List Filters
     ******************/

    // reset checkbox state (browser can remember)
    //$(".column-display-checkboxes input[type=checkbox]").removeAttr('checked');

    // checkbox clicks
    $('#display_price_columns_checkbox').on('click', function(){
        if($(this).is(":checked")){
            $.cookie("price_input", 'checked', { path: "/" });
            $('.col-price').show();
        }
        else{
            $.removeCookie("price_input", { path: '/' });
            $('.col-price').hide();
        }
    });
    if($.cookie("price_input")){
        $('#display_price_columns_checkbox').attr('checked', true);
        $('.col-price').show();
    }else{
        $('#display_price_columns_checkbox').attr('checked', false);
        $('.col-price').hide();
    }

    $('#display_people_columns_checkbox').on('click', function(){
        if($(this).is(":checked")){
            $.cookie("people_input", 'checked', { path: "/" });
            $('.col-requester, .col-requester-dept, .col-pm, .col-ae, .col-tsg').show();
        }
        else{
            $.removeCookie("people_input", { path: '/' });
            $('.col-requester, .col-requester-dept, .col-pm, .col-ae, .col-tsg').hide();
        }
    });
    if($.cookie("people_input")){
        $('#display_people_columns_checkbox').attr('checked', true);
        $('.col-requester, .col-requester-dept, .col-pm, .col-ae, .col-tsg').show();
    }else{
        $('#display_people_columns_checkbox').attr('checked', false);
        $('.col-requester, .col-requester-dept, .col-pm, .col-ae, .col-tsg').hide();
    }
    $('#display_est_date_columns_checkbox').on('click', function(){
        if($(this).is(":checked")){
            $.cookie("est_date_input", 'checked', { path: "/" });
            $('.col-estimate-due, .col-estimated, .col-estimate-number, .col-quote-due').show();
        }
        else{
            $.removeCookie("est_date_input", { path: '/' });
            $('.col-estimate-due, .col-estimated, .col-estimate-number, .col-quote-due').hide();
        }
    });
    if($.cookie("est_date_input")){
        $('#display_est_date_columns_checkbox').attr('checked', true);
        $('.col-estimate-due, .col-estimated, .col-estimate-number, .col-quote-due').show();
    }else{
        $('#display_est_date_columns_checkbox').attr('checked', false);
        $('.col-estimate-due, .col-estimated, .col-estimate-number, .col-quote-due').hide();
    }
    $('#display_job_date_columns_checkbox').on('click', function(){
        if($(this).is(":checked")){
            $.cookie("job_date_input", 'checked', { path: "/" });
            $('.col-started, .col-due, .col-delivered, .col-completed').show();
        }
        else{
            $.removeCookie("job_date_input", { path: '/' });
            $('.col-started, .col-due, .col-delivered, .col-completed').hide();
        }
    });
    if($.cookie("job_date_input")){
        $('#display_job_date_columns_checkbox').attr('checked', true);
        $('.col-started, .col-due, .col-delivered, .col-completed').show();
    }else{
        $('#display_job_date_columns_checkbox').attr('checked', false);
        $('.col-started, .col-due, .col-delivered, .col-completed').hide();
    }

    var url_param = window.location.search.slice(window.location.search.indexOf('?') + 1);
    var param_value = url_param.slice(url_param.indexOf('=') + 1);
    if(param_value.indexOf('&') != -1){
        param_value = param_value.slice(0, param_value.indexOf('&'));
    }
    if(param_value) {
        if (param_value[0] == '-') {
            var id_val = param_value.slice(param_value.indexOf('-') + 1);
            $('#'+id_val).find('.sort-icon').removeClass('fa fa-sort');
            $('#'+id_val).find('.sort-icon').addClass('fa fa-sort-desc');
        }
        else {
            $('#'+param_value).find('.sort-icon').removeClass('fa fa-sort');
            $('#'+param_value).find('.sort-icon').addClass('fa fa-sort-asc');
        }
    };

    $(".clickable-th").click(function() {
        window.document.location = $(this).data("href");
    });
});
