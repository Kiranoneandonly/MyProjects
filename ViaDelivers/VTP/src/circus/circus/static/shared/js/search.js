"use strict";

var search_setup = function(url) {
    var get_search_page = function() {
        var value = $('.search-query').val();
        window.location.assign(url + '?q=' + value);
    };
    $('#search').on('keypress', function(e) {
        e.stopPropagation();
        if ( e.keyCode == 13 ) {
            get_search_page();
        }
    });
    $('.search-submit').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        get_search_page();
    });
};
