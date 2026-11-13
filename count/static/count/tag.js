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
