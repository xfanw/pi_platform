"use strict";

function create_user() {
    Swal.fire({
        title: `New User`,
        html: `
                <div class='row col-md-12'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Username</div>
                      <input id="new_username" maxlength="150" required placeholder="first.last" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Display Name</div>
                      <input id="new_display_name" maxlength="150" required placeholder="First Last" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Email</div>
                      <input id="new_email" type="email" required placeholder="user@foxconn.com" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Temporary Password</div>
                      <input id="new_password" type="password" required placeholder="Enter temporary password" autocomplete="off">
                  </div>
                </div>
              `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Create`,
        allowOutsideClick: false,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                url: "/access/create_user",
                method: "POST",
                data: {
                    csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
                    username: $("#new_username").val(),
                    display_name: $("#new_display_name").val(),
                    email: $("#new_email").val(),
                    password: $("#new_password").val(),
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
