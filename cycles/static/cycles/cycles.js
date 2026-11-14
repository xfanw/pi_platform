// This is from base.html script
// function setChecks(name, checked) {
//     document.querySelectorAll('input[name="' + name + '"]').forEach((input) => (input.checked = checked));
// }
"use strict";

function review_cycle() {
    let pi_name = $("#cycle_name").val().trim();
    if (!pi_name) {
        show_top_right_error("Please enter a PI name.");
        return;
    }

    var sap_locations = $('input[name="sap_location_ids"]:checked')
        .map(function () {
            return this.value;
        })
        .get();

    var sap_count = sap_locations.length;
    if (sap_count === 0) {
        show_top_right_error("Please select at least one SAP location.");
        return;
    }

    var physical_locations = $('input[name="location_ids"]:checked')
        .map(function () {
            return this.value;
        })
        .get();
    var physical_count = physical_locations.length;
    if (physical_count === 0) {
        show_top_right_error("Please select at least one physical location.");
        return;
    }

    var sub_locations = $('input[name="sub_location_ids"]:checked')
        .map(function () {
            return this.value;
        })
        .get();
    var sub_location_count = sub_locations.length;
    if (sub_location_count === 0) {
        show_top_right_error("Please select at least one sub-location.");
        return;
    }

    Swal.fire({
        html: `
        <section class="card review-card">
          <div class="pane-title">Confirm new PI</div>
          <h2>${pi_name}</h2>
          <div class="cards review-kpis">
            <div class="kpi"><div class="lbl">SAP Locations</div><div class="val">${sap_count}</div></div>
            <div class="kpi"><div class="lbl">Physical Locations</div><div class="val">${physical_count}</div></div>
            <div class="kpi"><div class="lbl">Sub-locations</div><div class="val">${sub_location_count}</div></div>
          </div>
          <div class="flash warn"><b>Fresh PI:</b> PN List, Exclude PN List, Tag Range, SAP Book Inventory and Count Results start empty.</div>
        </section>
                `,
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Create`,
        allowOutsideClick: false,
        width: "700px",
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#cycle-create-form").submit();
        }
    }); // end swal
}
