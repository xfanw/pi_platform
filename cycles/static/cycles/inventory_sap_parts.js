"use strict";

function edit_sap_part(line_id) {
    $(`#quantity_${line_id}`).prop("disabled", false);
    $(`#edit_button_${line_id}`).hide();
    $(`#save_button_${line_id}`).show();
}
