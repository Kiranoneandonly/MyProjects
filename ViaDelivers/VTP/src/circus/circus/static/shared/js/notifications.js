/* VTP notifications.
 * Depends on jquery.cookie.js and underscore.js.
 */

/* global _ */
/* exported VTP_Notifications */

//noinspection JSUnusedGlobalSymbols
var VTP_Notifications = (function ($, _) {
    "use strict";

    var data = {
        timer: null,
        in_progress: [],
        complete: [],
        should_redirect: false
    };
    var api = {
        poll_interval: 10000,  // milliseconds
        COOKIE_NAME: 'in_progress',
        analysis_status_url: '/client/analysis_status',
        _data: data
    };

    api.start = function start() {
        api.poll();
        data.timer = setInterval(api.poll, api.poll_interval);
    };
    api.stop = function stop() {
        clearInterval(data.timer);
        data.timer = null;
    };
    api.poll = function poll() {
        var query, response;
        data.in_progress = api._get_projects();
        if (data.in_progress.length) {
            api._show("progress");
            query = {'projects': JSON.stringify(data.in_progress)};
            response = $.getJSON(api.analysis_status_url, query);
            // FIXME: no error handler added here. We could use a "report error
            // to developer" mechanism.
            response.then(api._poll_callback);
        }
    };
    api._poll_callback = function _poll_callback(result, status, jqXHR) {
        var complete, complete_ids;
        complete = _.where(result, {complete: true});

        if (complete.length) {
            api.notify(complete);
            api._data.complete = _.union(api._data.complete, complete);
            complete_ids = _.pluck(complete, 'id');
            api._data.in_progress = _.difference(
                api._data.in_progress, complete_ids);
        }
    };
//    api._poll_errback = function _poll_callback(result, status, jqXHR) {
//        console.log("errback", result, status, jqXHR);
//    };

    api._get_projects = function _get_projects() {
        var cookie_projects = $.cookie(api.COOKIE_NAME);
        cookie_projects = cookie_projects ? $.parseJSON(cookie_projects) : [];
        return _.union(data.in_progress, cookie_projects);
    };

    api._show = function _show(state) {
        var $analysis_complete = $(".analysis_complete");
        var $analysis_processing = $(".analysis_processing");
        if (state === 'progress') {
            // only show progress message if results have not been shown.
            if (!($analysis_complete.filter(':visible').length)) {
                $analysis_processing.show();
            }
        } else if (state === 'complete') {
            $analysis_processing.hide();
            $analysis_complete.show();
        } else if (state === 'dismiss') {
            $analysis_processing.hide();
            $analysis_complete.hide();
        }
    };

    api.notify = function notify(complete_projects) {
        // The API is written to let us check a list of projects, but the UI is
        // a lot more streamlined if we assume there's just one project, which
        // we think will be almost always true.
        var project = complete_projects[0];

        // There's a jumble of things going on here until we figure out which
        // UX we want.

        /* No message, just redirect. */
        if (data.should_redirect) {
            window.location = project.url;
        }

        /* Unobtrusive notification area at the top: */

        $(".analysis_complete .analysis_result_link").attr({
            href: project.url,
            title: project.name
        });
        api._show("complete");

        /* In-your-face modal notification. */

        var $modal = $("#analysis_complete_modal");
        $modal.find(".job-name").text(project.name);
        $modal.find(".btn-primary").click(function () {
            window.location = project.url;
        });
        $modal.modal();
    };


    api.redirect_on_completion = function redirect_on_completion(do_redirect) {
        data.should_redirect = do_redirect;
    };

    return api;
})(jQuery, _);
