"use strict";

function show_comments(part_number) {
    $.ajax({
        url: "/variance/get_comment",
        data: {
            part_number: part_number,
        },
        success: function (response) {
            if (response.status !== "success") {
                show_top_right_error(response.status || "error", response.msg || "Unable to load comments.");
                return;
            } else {
                const escapeHtml = (value) =>
                    String(value == null ? "" : value).replace(
                        /[&<>"']/g,
                        (character) =>
                            ({
                                "&": "&amp;",
                                "<": "&lt;",
                                ">": "&gt;",
                                '"': "&quot;",
                                "'": "&#39;",
                            })[character],
                    );
                const reviewRows = Array.isArray(response.review_rows) ? response.review_rows : [];
                const statusClasses = {
                    Posted: "posted",
                    "To Post": "to-post",
                    "Not Post": "not-post",
                    "Closed Resolved": "settled",
                };
                let html_text = "<div class='text-sm mut mb-2'>Only SAP Locations with a <b class='text-danger fw-bold'>non-zero</b> Live Variance are listed.</div>";
                html_text += `<div class='input-group'>
                <div class='input-group-text' style='width: 11em;'>SAP Location</div>
                <select class='form-select sap-location-select'>`;
                for (let i = 0; i < reviewRows.length; i++) {
                    html_text += `<option value="${i}">${escapeHtml(reviewRows[i].sap_code)}</option>`;
                }
                html_text += `</select></div>`;

                html_text += `<br>`;
                for (let i = 0; i < reviewRows.length; i++) {
                    let row = reviewRows[i];
                    let status = row.status || "Needs Review";
                    let statusClass = statusClasses[status] || "review";
                    let resolution = row.resolution || {};
                    html_text += `<div class="location-panel" data-location-panel="${i}" style="display:${i === 0 ? "" : "none"}">
                    <table class="table">
                    <thead>
                      <tr>
                        <th>SAP Location</th>
                        <th>Variance Qty</th>
                        <th>Variance Value</th>
                        <th>Status</th>
                        <th>SAP Doc</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td class='text-center'>${escapeHtml(row.sap_code)}</td>
                        <td class='text-center ${row.variance_quantity < 0 ? "neg" : row.variance_quantity > 0 ? "pos" : ""}'>${escapeHtml(row.variance_quantity)}</td>
                        <td class='text-center ${row.variance_value < 0 ? "neg" : row.variance_value > 0 ? "pos" : ""}'>${row.sap_inventory === "CONSIGNED" ? "—" : "$" + escapeHtml(row.variance_value)}</td>
                        <td class='text-center resolution-chip ${statusClass}'>${escapeHtml(status)}</td>
                        <td class='text-center'>${escapeHtml(resolution.sap_document_number || "-- --")}</td>
                      </tr>
                    </tbody>
                    </table>
                    `;
                    if (resolution.created_at) {
                        html_text += `<div class="variance-current-reason"><b>Decision note</b><span>${escapeHtml(resolution.reason)} by ${escapeHtml(resolution.created_by)} at ${escapeHtml(resolution.created_at)}</span></div>`;
                    }

                    html_text += `<div class="variance-thread">
                    <div class="variance-thread-title">Comment thread</div>`;
                    if (Array.isArray(row.comments) && row.comments.length > 0) {
                        for (let comment of row.comments) {
                            html_text += `<div class="variance-comment">
                      <div><span>${escapeHtml(comment.created_by)} at ${escapeHtml(comment.created_at)}</span></div>
                      <h5 class='text-start'>${escapeHtml(comment.body)}</h5>
                    </div>`;
                        }
                    } else {
                        html_text += `<p class="mut">No comments yet.</p>`;
                    }
                    html_text += `</div></div>`;
                }

                Swal.fire({
                    title: `Live Comments`,
                    html: html_text,
                    confirmButtonColor: "#3085d6",
                    confirmButtonText: `OK`,
                    width: "40%",
                    didOpen: () => {
                        const popup = Swal.getPopup();
                        const locationSelect = popup.querySelector(".sap-location-select");
                        if (!locationSelect) {
                            return;
                        }
                        const locationPanels = popup.querySelectorAll("[data-location-panel]");
                        const showSelectedLocation = () => {
                            locationPanels.forEach((panel) => {
                                panel.style.display = panel.dataset.locationPanel === locationSelect.value ? "" : "none";
                            });
                        };
                        locationSelect.addEventListener("change", showSelectedLocation);
                        showSelectedLocation();
                    },
                }).then(function (result) {
                    if (result.isConfirmed) {
                    }
                }); // end swal
            }
        },
        error: function () {
            show_json_message("error", "Connection Error.");
        },
    }); // end ajax
}
