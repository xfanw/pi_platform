"use strict";

$(function () {
    let selectedLocation = $("#pnVarianceLocation").val();
    set_display_panel(selectedLocation);
});

$("#pnVarianceLocation").change(function () {
    let selectedLocation = $(this).val();
    set_display_panel(selectedLocation);
});

function set_display_panel(selectedLocation) {
    $(".variance-review-list [data-location-panel]").each(function () {
        $(this).prop("hidden", $(this).attr("data-location-panel") !== selectedLocation);
        $(this).css("display", $(this).attr("data-location-panel") === selectedLocation ? "block" : "none");
    });
}
