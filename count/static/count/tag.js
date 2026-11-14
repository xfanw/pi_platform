"use strict";

function search_tag(tag_num = "") {
    if (tag_num === "") {
        tag_num = $("#count-tag-number").val();
    }
    window.location.href = `/count/count_tag?tag_number=${tag_num}`;
}

$("#count-tag-number").keydown(function (e) {
    if (e.key === "Enter") {
        e.preventDefault();
        search_tag();
    }
});

function edit_tag_part(tag_num, part_number, qty) {
    Swal.fire({
        title: `Tag Number: ${tag_num}`,
        html: `<form id='edit_tag_form' action='/count/count_tag_update'>
                  <input type='hidden' name='tag_number' value='${tag_num}'>
                  <div class='row col-md-12'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Part Number</div>
                        <input id="part_number"  name="part_number" maxlength="16" required placeholder="eg.TCGA" autocomplete="off" onkeyup='upper_case(this)' value="${part_number}">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Quantity</div>
                        <input name="quantity" required placeholder="eg.10" autocomplete="off" value="${qty}">
                    </div>
                  </div>
                </form>
                `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Update`,
        allowOutsideClick: false,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#edit_tag_form").submit();
        }
    }); // end swal
}
