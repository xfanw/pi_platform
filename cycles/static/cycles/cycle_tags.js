"use strict";

$("#sap_location").on("change", function () {
    const selected_sap = $(this).val();
    let loc_elem = $("#tag-add-location");

    // Clear second dropdown
    loc_elem.empty();
    loc_elem.append(
        $("<option>", {
            value: "",
            text: "Select SAP Location First",
        }),
    );

    let sub_elem = $("#tag-add-sub");
    sub_elem.empty();
    sub_elem.append(
        $("<option>", {
            value: "",
            text: "Select Location First",
        }),
    );

    if (selected_sap === "") {
        loc_elem.prop("disabled", true);
        sub_elem.prop("disabled", true);
        $("#start_number").prop("disabled", true);
        $("#end_number").prop("disabled", true);
        $("#add-range-button").prop("disabled", true);
        return;
    } else {
        loc_elem.prop("disabled", false);
    }
    // Populate matching tag-add-subs
    const filteredLocations = location_list.filter(function (location) {
        return location.sap_code === selected_sap;
    });
    $.each(filteredLocations, function (index, item) {
        loc_elem.append(
            $("<option>", {
                value: item.loc_name,
                text: item.loc_name + " / " + item.sap_code,
            }),
        );
    });
});

$("#tag-add-location").on("change", function () {
    const selected_location = $(this).val();
    let sub_elem = $("#tag-add-sub");

    // Clear second dropdown
    sub_elem.empty();

    sub_elem.append(
        $("<option>", {
            value: "",
            text: "Select Location First",
        }),
    );
    if (selected_location === "") {
        sub_elem.prop("disabled", true);
        $("#start_number").prop("disabled", true);
        $("#end_number").prop("disabled", true);
        $("#add-range-button").prop("disabled", true);
        return;
    } else {
        sub_elem.prop("disabled", false);
    }
    const filteredSubLocations = sub_location_list.filter(function (sub_location) {
        return sub_location.loc_name === selected_location;
    });
    $.each(filteredSubLocations, function (index, item) {
        sub_elem.append(
            $("<option>", {
                value: item.sub_name,
                text: item.sub_name + " / " + item.loc_name,
            }),
        );
    });
});

$("#tag-add-sub").on("change", function () {
    const selected_sub = $(this).val();
    if (selected_sub === "") {
        $("#start_number").prop("disabled", true);
        $("#end_number").prop("disabled", true);
        $("#add-range-button").prop("disabled", true);
    } else {
        $("#start_number").prop("disabled", false);
        $("#end_number").prop("disabled", false);
        $("#add-range-button").prop("disabled", false);
    }
});
