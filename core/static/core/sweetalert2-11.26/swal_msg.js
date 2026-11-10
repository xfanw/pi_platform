"use strict";

// json message
function show_json_message(status, msg, mode = "default") {
    if (mode !== "default") {
        show_static_message(status, msg);
        return;
    }
    if (status === "success") {
        show_top_right_success(msg);
    } else if (msg === "Connection Error.") {
        show_top_right_error(msg, "Contact PI Develoment Team");
    } else {
        show_top_right_error(msg);
    }
}

function hide_json_message() {
    $("#json-message").hide();
    // $("#bottomSection").hide();
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

// $(function () {
//     $.ajax({
//         url: "/api/server_type_api",
//         type: "GET",
//         success: function (response) {
//             if (response.server_type !== "PROD") {
//                 $("#server_type_div").text(`This is ${response.server_type} Server | MES DB: ${response.mes_db} |  MFE DB: ${response.mfe_db} !!!`);
//             }
//             $("#curr_version_div").text(`v ${response.curr_version}`);
//         },
//         error: function () {
//             show_json_message("error", "Connection Error.");
//         },
//     }); // end ajax
// });

function show_top_right_error(title, msg = "", time_out = 2000) {
    let title_a_length = title.substring(title.indexOf("<a"), title.indexOf("/a>")).length;
    if (msg === "" && title.length - title_a_length >= 40) {
        msg = title;
        title = "";
    }

    let width = 25;
    msg.split("<br>").forEach(function (line) {
        let line_substring = line.substring(line.indexOf("<a"), line.indexOf("/a>"));
        let line_length = line.replace(line_substring, "").length;
        if (line_length >= 90) {
            width = Math.max(width, 55);
        } else if (line_length >= 75) {
            width = Math.max(width, 45);
        } else if (line_length >= 45) {
            width = Math.max(width, 35);
        }
    });
    Swal.fire({
        icon: "error",
        title: title,
        html: `${msg}`,
        allowOutsideClick: false,
        allowEscapeKey: false,
        width: `${width}%`,
        confirmButtonColor: "#3085d6",
        confirmButtonText: `OK`,
        didOpen: () => {
            swal_delay_confirm(time_out);
        },
    }); // end Swal
}

function show_top_right_success(msg, time_out = 2000) {
    Swal.fire({
        toast: true,
        position: "top-right",
        customClass: {
            popup: "colored-toast",
        },
        showConfirmButton: false,
        timer: time_out,
        timerProgressBar: true,
        iconColor: "#198754",
        icon: "success",
        title: msg,
        width: "450px",
    });
}

function show_static_message(status, msg) {
    let html = msg
        .split(",")
        .map((item) => {
            item = item.trim();
            item = item.replace(/"([^"]+)"/g, '<span class="badge bg-primary">$1</span>');

            return `<div class="text-start mb-2">• ${item}</div>`;
        })
        .join("");

    Swal.fire({
        icon: status === "success" ? "success" : "warning",
        title: status === "success" ? "Success" : "Please Confirm",
        html: html,
        allowOutsideClick: false,
        allowEscapeKey: false,
        confirmButtonColor: "#3085d6",
        confirmButtonText: "OK",
        width: "650px",
        customClass: {
            htmlContainer: "swal2-text-left",
        },
    });
}

// Pattern Check
// !Perfect function, DO NOT CHANGE
function check_input_pattern(elem, positive_num = true) {
    let val = $(elem).val();
    let pattern = new RegExp($(elem).attr("pattern"));

    if (positive_num) {
        if (val.includes("e") || val.includes("-")) {
            $(elem).val(val.slice(0, -1));
            if (!pattern.test($(elem).val())) {
                $(elem).val("");
            }
            return false;
        }
    }

    if (pattern.test(val)) {
        if (val.startsWith(".")) {
            $(elem).val(`0${val}`);
        }
        return true;
    } else {
        $(elem).val(val.slice(0, -1));
        if (!pattern.test($(elem).val())) {
            $(elem).val("");
        }
        return false;
    }
}

// The following function are used to change displaying of result status
const mark_pending = (elem) => {
    elem.removeClass("bg-success bg-danger").val("Pending");
};

const mark_pass = (elem) => {
    elem.removeClass("bg-danger").addClass("bg-success").val("PASS");
};

const mark_fail = (elem) => {
    elem.removeClass("bg-success").addClass("bg-danger").val("FAIL");
};

function swal_delay_confirm(time_out = 3000) {
    // Disable confirm button
    Swal.getConfirmButton().disabled = true;
    let swal_inner_count_down = setInterval(() => {
        time_out -= 100;
        Swal.getConfirmButton().textContent = `Read Instructions (${Math.ceil(time_out / 1000)})`;
    }, 100);

    // Re-enable after specified timeout
    setTimeout(() => {
        clearInterval(swal_inner_count_down);
        Swal.getConfirmButton().disabled = false;
        Swal.getConfirmButton().textContent = "Confirm";
    }, time_out);
}
