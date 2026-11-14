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

function edit_tag_part(tag_num) {
    Swal.fire({
        title: `Tag Number: ${tag_num}`,
        html: `<form id='new_plant_form' action='/site_setting/create_plant'>
                  <div class='row col-md-12'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Plant Code</div>
                        <input id="plant_code"  name="plant_code" maxlength="16" required placeholder="eg.TCGA" autocomplete="off" onkeyup='upper_case(this)'>
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Plant Name</div>
                        <input name="plant_name" required placeholder="eg.Texas Campus A" autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Site</div>
                        <input name="site" required placeholder="eg.FII-USA" autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'>Customer</div>
                        <input name="customer" required autocomplete="off">
                    </div>
                  </div>
                  <div class='row col-md-12 mt-2'>
                    <div class='input-group'>
                        <div class='input-group-text' style='min-width:11em'> Time Zone</div>
                        <select class='form-control' name='timezone'>${timezone_option}</select>
                    </div>
                  </div>
                </form>
                `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Create`,
        allowOutsideClick: false,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#new_plant_form").submit();
        }
    }); // end swal
}
