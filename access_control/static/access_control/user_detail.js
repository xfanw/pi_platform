"use strict";

function edit_profile() {
    $("#display_name").removeAttr("readonly");
    $("#email").removeAttr("readonly");
    $("#status").removeAttr("disabled");
    $("#save_profile_button").show();
    $("#edit_profile_button").hide();
}

function reset_password(user_id) {
    Swal.fire({
        title: `Reset Temporary Password`,
        html: ` <div class='row col-md-12'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>New Password</div>
                      <input class='form-control' id="new_password" type='password' placeholder="new_password" autocomplete="new-password">
                      <button class="btn btn-outline-secondary" type="button" title="Show/Hide password" onclick='toggle_password()'>
                          <i id='password_icon' class="fa-solid fa-eye-slash text-primary"></i>
                      </button>
                  </div>
                </div>
              `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Confirm`,
        allowOutsideClick: false,
    }).then(function (result) {
        if (result.isConfirmed) {
            let new_password = $("#new_password").val().trim();
            if (new_password === "") {
                show_top_right_error("Password", "Password CANNOT be empty.");
                return;
            }
            $.ajax({
                url: `/access/reset_password/${user_id}`,
                method: "POST",
                data: {
                    csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
                    password: new_password,
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
    }); // end swal
}

function toggle_password() {
    const password_input = $("#new_password");

    const currentType = password_input.attr("type");
    password_input.attr("type", currentType === "password" ? "text" : "password");

    $("#password_icon").toggleClass("fa-eye fa-eye-slash");
}

function toggle_admin() {
    let selected_role = $("#role").val();
    if (selected_role === "Global Admin") {
        $("#plant").prop("disabled", true).addClass("bg-secondary");
        $("#department").prop("disabled", true).addClass("bg-secondary");
        $("#sap_location").prop("disabled", true).addClass("bg-secondary");
    } else {
        $("#plant").prop("disabled", false).removeClass("bg-secondary");
        $("#department").prop("disabled", false).removeClass("bg-secondary");
        $("#sap_location").prop("disabled", false).removeClass("bg-secondary");
    }
}

function set_ownership() {
    const plant_code = $("#plant").val();
    const $department = $("#department");
    const departments = [...new Set(sap_locations.filter((location) => location.plant__code === plant_code).map((location) => location.department))];

    $department.empty().append(
        $("<option>", {
            value: "",
            text: "-- All --",
        }),
    );

    departments.forEach((department) => {
        $department.append(
            $("<option>", {
                value: department,
                text: `${plant_code} / ${department}`,
            }),
        );
    });

    set_sap_location();
}

function set_sap_location() {
    const department = $("#department").val().trim();
    const plant_code = $("#plant").val().trim();

    const $sapLocation = $("#sap_location");

    // Reset SAP location dropdown
    $sapLocation.empty();
    $sapLocation.append(
        $("<option>", {
            value: "",
            text: "-- All --",
        }),
    );

    // Filter locations by department and plant
    const filteredLocations = sap_locations.filter(function (location) {
        return location.department === department && location.plant__code === plant_code;
    });

    // Populate matching locations
    $.each(filteredLocations, function (index, location) {
        $sapLocation.append(
            $("<option>", {
                value: location.code,
                text: `${plant_code} / ${location.code}`,
            }),
        );
    });
}

function remove_role(username, role, role_id) {
    Swal.fire({
        title: `Delete Role from User`,
        html: `Role <b class='text-danger'>${role}</b> will be removed from User <b class='text-danger'>${username}</b>. <br><br>
              Do you want to continue?
              `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Create`,
        allowOutsideClick: false,
        didOpen: () => {
            swal_delay_confirm();
        },
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                url: `/access/remove_user_role/${role_id}`,
                method: "GET",
                data: {},
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
    }); // end swal
}
