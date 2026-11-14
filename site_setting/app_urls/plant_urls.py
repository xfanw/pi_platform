from site_setting.app_views.plant import (
    plant_setup,
    create_plant,
    update_plant,
    create_sap_location,
    update_sap_location,
)
from django.urls import path

urlpatterns = [
    path("plant", plant_setup, name="plant_setup"),
    path("create_plant", create_plant, name="create_plant"),
    path("update_plant", update_plant, name="update_plant"),
    path("create_sap_location", create_sap_location, name="create_sap_location"),
    path("update_sap_location/<slug:sap_loc_id>", update_sap_location, name="update_sap_location"),
]
