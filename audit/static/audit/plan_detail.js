"user strict";

function show_candidate_detail(candidate_id) {
    // Implement the logic to show candidate detail here
    console.log("Show details for candidate:", candidate_id);
    $.ajax({
        url: `/audit/audit_candidate_detail/${candidate_id}`,
        method: "GET",
        success: function (response) {
            if (response.status === "error") {
                show_top_right_error(response.message);
            } else {
                let html = `<form action='/audit/audit_candidate_update/${candidate_id}' method='GET' id='audit-candidate-detail-form'>`;
                html +=
                    "<div class='audit-candidate-wrap'><table class='audit-candidate-table table-center'><thead><tr><th>ID</th><th>Selected</th><th>Part Number</th><th>Count Quantity</th><th>Physical Location</th><th>Sub Location</th><th>Tag Number</th></tr></thead><tbody>";

                response.data.forEach(function (record) {
                    html += `<tr>
                        <td><input type='checkbox' ${record.selected ? "checked" : ""} value='${record.id}' name='selected_record'></td>
                        <td>${record.selected}</td>
                        <td>${record.part_number_snapshot}</td>
                        <td>${record.count_quantity_snapshot}</td>
                        <td>${record.physical_location_snapshot}</td>
                        <td>${record.sub_location_snapshot}</td>
                        <td>${record.tag_number_snapshot}</td>
                    </tr>`;
                });
                html += "</tbody></table></div></form>";
                Swal.fire({
                    title: "Candidate Detail",
                    html: html,
                    width: "70%",
                    showCancelButton: true,
                    confirmButtonColor: "#3085d6",
                    cancelButtonColor: "#d33",
                    confirmButtonText: `Manual Change !!!`,
                    allowOutsideClick: false,
                }).then((result) => {
                    if (result.isConfirmed) {
                        $("#audit-candidate-detail-form").submit();
                    }
                }); //end Swal
            }
        },
        error: function () {
            show_top_right_error("Connection Error.");
        },
    }); //end ajax
}

function show_candidate_detail_readonly(candidate_id) {
    // Implement the logic to show candidate detail here
    console.log("Show details for candidate:", candidate_id);
    $.ajax({
        url: `/audit/audit_candidate_detail/${candidate_id}`,
        method: "GET",
        success: function (response) {
            if (response.status === "error") {
                show_top_right_error(response.message);
            } else {
                let html =
                    "<div class='audit-candidate-wrap'><table class='audit-candidate-table table-center'><thead><tr><th>ID</th><th>Selected</th><th>Part Number</th><th>Count Quantity</th><th>Physical Location</th><th>Sub Location</th><th>Tag Number</th></tr></thead><tbody>";

                response.data.forEach(function (record) {
                    html += `<tr>
                        <td><input type='checkbox' ${record.selected ? "checked" : ""} disabled></td>
                        <td>${record.selected}</td>
                        <td>${record.part_number_snapshot}</td>
                        <td>${record.count_quantity_snapshot}</td>
                        <td>${record.physical_location_snapshot}</td>
                        <td>${record.sub_location_snapshot}</td>
                        <td>${record.tag_number_snapshot}</td>
                    </tr>`;
                });
                html += "</tbody></table></div>";
                Swal.fire({
                    title: "Candidate Detail",
                    html: html,
                    width: "70%",
                    showCancelButton: true,
                    confirmButtonColor: "#3085d6",
                    cancelButtonColor: "#d33",
                    confirmButtonText: `Manual Change !!!`,
                    allowOutsideClick: false,
                }).then((result) => {
                    if (result.isConfirmed) {
                        let selectedRecords = [];
                        $("input[name='selected_record']:checked").each(function () {
                            selectedRecords.push($(this).val());
                        });
                        console.log("Selected records:", selectedRecords);
                        // Implement the logic for the "Create" button here
                        console.log("Create button clicked");
                    }
                }); //end Swal
            }
        },
        error: function () {
            show_top_right_error("Connection Error.");
        },
    }); //end ajax
}
