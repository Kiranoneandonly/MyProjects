"use strict";

$(function() {
    // setup task assets to show/hide on click
    $('.task-group-toggle').click(function(e) {
        var taskGroupToggle = $('#' + e.currentTarget.id + ' i');
        var taskGroupId = e.currentTarget.id.replace('Toggle', '');
        var taskGroup = $('#' + taskGroupId);
        if (taskGroup.is(':hidden')) {
            taskGroup.show();
            taskGroupToggle.removeClass('fa-plus').addClass('fa-minus');
        } else {
            // hide task asset rows if shown
            var taskAssetToggle = taskGroup.find('.task-asset-toggle i');
            var taskAsset = taskGroup.find('.task-asset-row');
            if (taskAsset.is(':visible')) {
                taskAsset.hide();
                taskAssetToggle.removeClass('fa-minus').addClass('fa-plus');
            }
            // hide task groups
            taskGroup.hide();
            taskGroupToggle.removeClass('fa-minus').addClass('fa-plus');
        }
    });

    // task assets initially hidden
    $('.task-asset-row').hide();

    // setup task assets to show/hide on click
    $('.task-asset-toggle').click(function(e) {
        var taskAssetToggle = $('#' + e.currentTarget.id + ' i');
        var taskAssetClass = e.currentTarget.id.replace('Toggle', '');
        var taskAsset = $('.' + taskAssetClass);
        if (taskAsset.is(':hidden')) {
            taskAsset.show();
            taskAssetToggle.removeClass('fa-plus').addClass('fa-minus');
        } else {
            taskAsset.hide();
            taskAssetToggle.removeClass('fa-minus').addClass('fa-plus');
        }
    });
});
