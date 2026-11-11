"use strict";

$("#sap_location").on("change", function () {
    const selected_sap = $(this).val();
    let loc_elem = $("#location");

    // Clear second dropdown
    loc_elem.empty();
    loc_elem.append(
        $("<option>", {
            value: "",
            text: "Select SAP Location First",
        }),
    );

    let sub_elem = $("#sub_location");
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
        $("#part_number").prop("disabled", true);
        $("#quantity").prop("disabled", true);
        $("#add-part-button").prop("disabled", true);
        return;
    } else {
        set_counter_roster(selected_sap);
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

$("#location").on("change", function () {
    const selected_location = $(this).val();
    let sub_elem = $("#sub_location");

    // Clear second dropdown
    sub_elem.empty();

    sub_elem.append(
        $("<option>", {
            value: "",
            text: "N/A",
        }),
    );
    if (selected_location === "") {
        sub_elem.prop("disabled", true);
        $("#part_number").prop("disabled", true);
        $("#quantity").prop("disabled", true);
        $("#add-part-button").prop("disabled", true);
        return;
    } else {
        sub_elem.prop("disabled", false);
        $("#part_number").prop("disabled", false);
        $("#quantity").prop("disabled", false);
        $("#add-part-button").prop("disabled", false);
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

function set_counter_roster(selected_sap) {
    let counter_elem = $("#counter_name");
    counter_elem.empty();

    counter_elem.append(
        $("<option>", {
            value: "",
            text: "Select SAP Location First",
        }),
    );

    let counter_list = $.map(counter_roster_list, function (item) {
        if (item.sap_location__code === selected_sap) {
            return item.display_name;
        }
    });

    counter_list = counter_list.concat(plant_counter);

    // remove duplicates in counter list and order it
    counter_list = Array.from(new Set(counter_list)).sort();
    if (counter_list) {
        $.each(counter_list, function (index, item) {
            counter_elem.append(
                $("<option>", {
                    value: item,
                    text: item,
                }),
            );
        });
    }
}
// function confirm_remove(range_id) {
//     Swal.fire({
//         title: "Are you sure?",
//         text: "Remove this unused Tag Range?",
//         showCancelButton: true,
//         confirmButtonColor: "#3085d6",
//         cancelButtonColor: "#d33",
//         confirmButtonText: `Create`,
//         allowOutsideClick: false,
//         didOpen: () => {
//             swal_delay_confirm();
//         },
//     }).then((result) => {
//         if (result.isConfirmed) {
//             location.href = "/cycles/tag_range_remove/" + range_id;
//         }
//     });
// }
