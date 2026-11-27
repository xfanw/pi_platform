"use strict";

function confirm_reverse(batch_id) {
    Swal.fire({
        title: "Reverse Batch Records?",
        text: "You are about to reverse all count results in this batch.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        didOpen: () => {
            swal_delay_confirm(2000);
        },
    }).then((result) => {
        if (result.isConfirmed) {
            show_loader(true);
            window.location.href = `/count/count_batch_revoke/${batch_id}`;
        }
    });
}
