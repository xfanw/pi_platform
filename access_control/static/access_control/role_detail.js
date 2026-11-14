"use strict";

function edit_role() {
    $("#role_scope").removeAttr("disabled");
    $("#role_holder").removeAttr("disabled");
    $("#description").removeAttr("disabled");
    $("#save_role_button").show();
    $("#edit_role_button").hide();
}

function save_role(role_id) {
    let role_scope = $("#role_scope").val();
    let role_holder = $("#role_holder").val();
    let description = $("#description").val();

    $.ajax({
        url: `/access/save_role_info/${role_id}`,
        method: "POST",
        data: {
            csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
            role_scope: role_scope,
            role_holder: role_holder,
            description: description,
        },
        success: function (response) {
            show_json_message(response.status, response.msg);
            if (response.status == "success") {
                $("#role_scope").prop("disabled", true);
                $("#role_holder").prop("disabled", true);
                $("#description").prop("disabled", true);
                $("#edit_role_button").show();
                $("#save_role_button").hide();
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
}

function group_add_app(group_name, app_name, counter) {
    let can_edit = $(`#edit_${counter}`).is(":checked");

    $.ajax({
        url: "/access/add_role_access",
        type: "GET",
        dataType: "json",
        data: {
            group_name: group_name,
            app_name: app_name,
            can_edit: can_edit,
        },
        success: function (response) {
            show_json_message(response.status, response.msg);
            if (response.status === "success") {
                setTimeout(function () {
                    location.reload();
                }, 1000);
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
}

function group_remove_app(perm_id) {
    $.ajax({
        url: `/access/remove_role_access/${perm_id}`,
        type: "GET",
        dataType: "json",
        data: {
            perm_id: perm_id,
        },
        success: function (response) {
            show_json_message(response.status, response.msg);
            if (response.status === "success") {
                setTimeout(function () {
                    location.reload();
                }, 1000);
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
}
