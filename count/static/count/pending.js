"use strict";
function add_part(item_id, raw_part_no) {
    Swal.fire({
        title: `Approve as new P/N<b class='text-danger'>${raw_part_no}</b>?`,
        html: `<form id='new_part_form' action='/count/pending_part_create'>
                <input type="hidden" name="item_id" value="${item_id}">
                <input type="hidden" name="part_number" value="${raw_part_no}">
                <div class='row col-md-12'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Part Desc</div>
                      <input name="description" maxlength="64" required placeholder="eg.Description" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>MAP $</div>
                      <input type="number" step="0.0001" name="price" required placeholder="eg.100" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Business Unit</div>
                      <input name="business_unit" required placeholder="eg.BU A" autocomplete="off">
                  </div>
                </div>
                <div class='row col-md-12 mt-2'>
                  <div class='input-group'>
                      <div class='input-group-text' style='min-width:11em'>Note &nbsp;<small class='mut'> (Optional)</small></div>
                      <input name="note" placeholder="Review Note" autocomplete="off">
                  </div>
                </div>
              </form>`,
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
            $("#new_part_form").submit();
        }
    }); // end swal
}
function map_part(item_id, raw_part_no) {
    // Implement the mapping logic here
    Swal.fire({
        title: `Map <b class='text-danger'>${raw_part_no}</b> to Existing P/N?`,
        html: `<form id='map_part_form' action='/count/pending_part_map'>
                <input type="hidden" name="item_id" value="${item_id}">
                <input type="text" id="existing_part_number" name="existing_part_number" placeholder="Enter existing part number" value="" autocomplete="off">
              </form>`,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Map`,
        allowOutsideClick: false,
        didOpen: () => {
            swal_delay_confirm();
        },
    }).then(function (result) {
        if (result.isConfirmed) {
            if (!$("#existing_part_number").val().trim()) {
                show_top_right_error("Existing part number is required.");
                return;
            }
            $("#map_part_form").submit();
        }
    }); // end swal
}

function reject_part(item_id, raw_part_no) {
    // Implement the rejection logic here
    Swal.fire({
        title: `Reject <b class='text-danger'>${raw_part_no}</b>?`,
        html: `<form id='reject_part_form' action='/count/pending_part_reject'>
                <input type="hidden" name="item_id" value="${item_id}">
                <input type="text" id="note" name="note" placeholder="Enter rejection reason" value="" autocomplete="off">
              </form>`,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Reject`,
        allowOutsideClick: false,
        didOpen: () => {
            swal_delay_confirm(1000);
        },
    }).then(function (result) {
        if (result.isConfirmed) {
            if (!$("#note").val().trim()) {
                show_top_right_error("Rejection reason is required.");
                return;
            }
            $("#reject_part_form").submit();
        }
    }); // end swal
}
