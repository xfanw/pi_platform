"use strict";
$("input").attr("autocomplete", "off");

function upper_case(elem) {
    $(elem).val($(elem).val().toUpperCase());
}

function show_under_developing() {
    Swal.fire({
        title: "Under Development",
        text: "This feature is under development.",
    });
}

function show_loader(show_text = false) {
    $("body").addClass("loader-open");
    $("#loader-modal").show();
    if (show_text) {
        $("#loader-modal-text").show();
    } else {
        $("#loader-modal-text").hide();
    }
}

function hide_loader() {
    $("#loader-modal").hide();
    $("#loader-modal-text").hide();
    $("body").removeClass("loader-open");
}
