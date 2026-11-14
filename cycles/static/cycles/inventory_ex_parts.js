"use strict";

function remove_ex_part(ex_part_id) {
    Swal.fire({
        title: "Are you sure?",
        text: "Remove this excluded part?",
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: `Remove`,
        allowOutsideClick: false,
        didOpen: () => {
            swal_delay_confirm(1000);
        },
    }).then((result) => {
        if (result.isConfirmed) {
            location.href = "/cycles/ex_part_delete/" + ex_part_id;
        }
    });
}
