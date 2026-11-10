"use strict";

function edit_part(part_id) {
    $(`#description_${part_id}`).prop("disabled", false);
    $(`#business_unit_${part_id}`).prop("disabled", false);
    $(`#price_${part_id}`).prop("disabled", false);
    $(`#edit_button_${part_id}`).hide();
    $(`#save_button_${part_id}`).show();
}
