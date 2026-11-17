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
