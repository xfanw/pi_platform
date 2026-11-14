"use strict";

$(function () {
    $("#sys_setting_header").click();
    adjust_text_area_height();
});

function adjust_text_area_height() {
    let txa = $("#list_content");
    txa.height(txa.prop("scrollHeight"));
}

function delete_var(var_name, var_value) {
    $.ajax({
        url: "/site_setting/change_system_list_settings",
        type: "GET",
        data: {
            var_name: var_name,
            var_action: "delete",
            var_value: var_value,
        },
        success: function (response) {
            show_json_message(response.status, response.msg);
            if (response.status === "success") {
                setTimeout(function () {
                    location.reload();
                }, 700);
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
}

function add_var(var_name) {
    hide_json_message();

    Swal.fire({
        title: `ADD value to ${var_name}`,
        html: `
            <div class='col-md-12 row'>
              <div class='input-group mb-3'>
                    <label class='input-group-text'>New Value:</label>
                    <input id='new_value' class='form-control' autocomplete='off'>
              </div>
            </div>
                `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Confirm`,
    }).then(function (result) {
        if (result.isConfirmed) {
            show_loader();

            $.ajax({
                url: "/site_setting/change_system_list_settings",
                type: "GET",
                data: {
                    var_name: var_name,
                    var_action: "add",
                    var_value: $("#new_value").val(),
                },
                success: function (response) {
                    hide_loader();

                    show_json_message(response.status, response.msg);
                    if (response.status === "success") {
                        setTimeout(function () {
                            location.reload();
                        }, 700);
                    }
                },
                error: function () {
                    hide_loader();
                    show_json_message("error", "Connection Error.");
                },
            }); // end ajax
        }
    }); // end Swal
}
