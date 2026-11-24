"use strict";

$(function () {
    calc_totel();
    calc_mix_total();
    $("#audit-auditors, #audit-pages, #audit-density, #audit-exclude-keywords, .mix-input").keydown(function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
        }
    });
});

$("#audit-auditors, #audit-pages, #audit-density").on("input change", calc_totel);
function calc_totel() {
    var auditors = Number($("#audit-auditors").val());
    var pages = Number($("#audit-pages").val());
    var density = Number($("#audit-density").val());
    var target = auditors * pages * density;
    $("#audit-target").text(target);
}

$("#audit-exclude-keywords").keydown(function () {
    $("#audit-exclude-apply").click();
});

$("#value-pct, #map-pct, #variance-pct").on("input change", calc_mix_total);

function calc_mix_total() {
    var value_pct = Number($("#value-pct").val());
    var map_pct = Number($("#map-pct").val());
    var variance_pct = Number($("#variance-pct").val());
    var total = (value_pct + map_pct + variance_pct).toFixed(2);
    $("#mix-total").text(total + "%");
    if (Number(total) == 100) {
        $("#generate-recommendation").prop("disabled", false);
    } else {
        $("#generate-recommendation").prop("disabled", true);
    }
}
