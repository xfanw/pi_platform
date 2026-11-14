"use strict";
function edit_location(location_id) {
    $(`#is_active_${location_id}`).removeAttr("data-readonly");
    $(`#edit_button_${location_id}`).hide();
    $(`#save_button_${location_id}`).show();
}

function cancel_location(location_id) {}
