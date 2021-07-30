$(function() {
    /* Don't let errors fade away without being acknowledged. */
    var $alerts = $(".alert").not('.alert-error, .alert-danger, .alert-display-always');

    $alerts.delay(5000).fadeOut("slow", function () { $(this).remove(); });
});
