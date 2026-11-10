"use strict";

function create_plant() {
    let timezone_option = "";
    for (let [loc, zone] of Object.entries(timezone_dict)) {
        if (loc === "America/Chicago") {
            timezone_option += `<option value='${loc}' selected>${zone} ${loc}</option>`;
        } else {
            timezone_option += `<option value='${loc}'>${zone} ${loc}</option>`;
        }
    }
    Swal.fire({
        title: `New Plant`,
        html: `<form id='new_plant_form' action='/site_setting/create_plant'>
                  <div class='row col-md-12'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Plant Code</div>
                        <input id="plant_code"  name="plant_code" maxlength="16" required placeholder="eg.TCGA" autocomplete="off" onkeyup='upper_case(this)'>
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Plant Name</div>
                        <input name="plant_name" required placeholder="eg.Texas Campus A" autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Site</div>
                        <input name="site" required placeholder="eg.FII-USA" autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Customer</div>
                        <input name="customer" required autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'> Time Zone</div>
                        <select class='form-control' name='timezone'>${timezone_option}</select>
                    </div>
                  </div>
                </form>
                `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Create`,
        allowOutsideClick: false,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#new_plant_form").submit();
        }
    }); // end swal
}

function create_plant_warning() {
    Swal.fire({
        title: `Warning`,
        text: `Only Global Admin can create a new plant.`,
        icon: `warning`,
        confirmButtonColor: "#3085d6",
        allowOutsideClick: false,
        didOpen: () => {
            swal_delay_confirm(2000);
        },
    }); // end swal
}

function edit_plant() {
    $("#plan_name").prop("disabled", false);
    $("#site").prop("disabled", false);
    $("#timezone").prop("disabled", false);
    $("#customer").prop("disabled", false);
    $("#status").prop("disabled", false);
    $("#save_plant_button").show();
    $("#edit_plant_button").hide();
}

function save_plant() {
    let plant_code = $("#plan_code").val();
    let plant_name = $("#plan_name").val();
    let site = $("#site").val();
    let timezone = $("#timezone").val();
    let customer = $("#customer").val();
    let status = $("#status").val();

    $.ajax({
        url: "/site_setting/update_plant",
        method: "POST",
        data: {
            csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
            plant_code: plant_code,
            plant_name: plant_name,
            site: site,
            timezone: timezone,
            customer: customer,
            status: status,
        },
        success: function (response) {
            show_json_message(response.status, response.msg);
            if (response.status == "success") {
                $("#save_plant_button").hide();
                $("#plan_name").prop("disabled", true);
                $("#site").prop("disabled", true);
                $("#timezone").prop("disabled", true);
                $("#customer").prop("disabled", true);
                $("#status").prop("disabled", true);
                $("#edit_plant_button").show();
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
} // end save_plant

function edit_sap_location(sap_location_id) {
    $(`#department_id_${sap_location_id}`).prop("disabled", false);
    $(`#code_${sap_location_id}`).prop("disabled", false);
    $(`#inventory_type_${sap_location_id}`).prop("disabled", false);
    $(`[id^='count_methods_${sap_location_id}']`).prop("disabled", false);
    $(`#address_${sap_location_id}`).prop("disabled", false);
    $(`#is_active_${sap_location_id}`).removeAttr("data-readonly");
    $(`#edit_button_${sap_location_id}`).hide();
    $(`#save_sap_location_button_${sap_location_id}`).show();
}

function cancel_sap_location(sap_location_id) {
    $(`#department_id_${sap_location_id}`).prop("disabled", true);
    $(`#code_${sap_location_id}`).prop("disabled", true);
    $(`#inventory_type_${sap_location_id}`).prop("disabled", true);
    $(`[id^='count_methods_${sap_location_id}']`).prop("disabled", true);
    $(`#address_${sap_location_id}`).prop("disabled", true);
    $(`#is_active_${sap_location_id}`).prop("data-readonly", "true");
    $(`#edit_button_${sap_location_id}`).show();
    $(`#save_sap_location_button_${sap_location_id}`).hide();
}
