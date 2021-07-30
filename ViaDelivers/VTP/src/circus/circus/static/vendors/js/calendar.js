"use strict";

/* globals event_data */

$(document).ready(function(){
    $('#calendar').fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,basicWeek,basicDay,listDay'
        },
        editable: false,
        displayEventTime: true,
        displayEventEnd: true,
        timezone: "local",
        timeFormat: 'H:mm', // uppercase H for 24-hour clock
        eventLimit: true,
        events: event_data,
        views: {
            month: {
                // options apply to Month views
                eventLimit: 10
            },
            basic: {
                // options apply to basicWeek and basicDay views
                eventLimit: 10
            },
            agenda: {
                // options apply to agendaWeek and agendaDay views
            },
            week: {
                // options apply to basicWeek and agendaWeek views
            },
            day: {
                // options apply to basicDay and agendaDay views
            }
        }
    });
});
