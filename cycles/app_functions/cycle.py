from datetime import datetime

from cycles.models import CyclePhysicalLocation, CycleSAPLocation, CycleSubLocation


def gen_cycle_name(plant_code):
    last_season = (datetime.now().month - 1) // 3
    curr_year = datetime.now().year
    if last_season == 0:
        curr_year -= 1
        last_season = 4
    return f"{plant_code} Q{last_season} {curr_year} PI"


def add_sap_location_to_cycle(cycle_ref, sap_loc_ref, curr_user):
    # Implement the logic to add the SAP location to the cycle
    CycleSAPLocation.objects.update_or_create(
        cycle=cycle_ref,
        sap_location=sap_loc_ref,
        defaults={"is_active": sap_loc_ref.is_active, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": sap_loc_ref.is_active,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )

    location_set = CyclePhysicalLocation.objects.filter(cycle=cycle_ref, physical_location__sap_location=sap_loc_ref, is_active=True)
    for cycle_physical_loc_ref in location_set:
        add_physical_location_to_cycle(cycle_ref, cycle_physical_loc_ref.physical_location, curr_user)


def add_physical_location_to_cycle(cycle_ref, physical_loc_ref, curr_user):
    # Implement the logic to add the physical location to the cycle
    CyclePhysicalLocation.objects.update_or_create(
        cycle=cycle_ref,
        physical_location=physical_loc_ref,
        defaults={"is_active": physical_loc_ref.is_active, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": physical_loc_ref.is_active,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )

    sub_loc_set = CycleSubLocation.objects.filter(cycle=cycle_ref, sub_location__physical_location=physical_loc_ref, is_active=True)
    for cycle_sub_loc_ref in sub_loc_set:
        add_sub_location_to_cycle(cycle_ref, cycle_sub_loc_ref.sub_location, curr_user)


def add_sub_location_to_cycle(cycle_ref, sub_loc_ref, curr_user):
    # Implement the logic to add the sub location to the cycle
    CycleSubLocation.objects.update_or_create(
        cycle=cycle_ref,
        sub_location=sub_loc_ref,
        defaults={"is_active": sub_loc_ref.is_active, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": sub_loc_ref.is_active,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )


def remove_sap_location_from_cycle(cycle_ref, sap_loc_ref, curr_user):
    # Implement the logic to remove the SAP location from the cycle
    CycleSAPLocation.objects.update_or_create(
        cycle=cycle_ref,
        sap_location=sap_loc_ref,
        defaults={"is_active": False, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": False,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )

    location_set = CyclePhysicalLocation.objects.filter(cycle=cycle_ref, physical_location__sap_location=sap_loc_ref, is_active=True)
    for cycle_physical_loc_ref in location_set:
        remove_physical_location_from_cycle(cycle_ref, cycle_physical_loc_ref.physical_location, curr_user)


def remove_physical_location_from_cycle(cycle_ref, physical_loc_ref, curr_user):
    # Implement the logic to remove the physical location from the cycle
    CyclePhysicalLocation.objects.update_or_create(
        cycle=cycle_ref,
        physical_location=physical_loc_ref,
        defaults={"is_active": False, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": False,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )

    sub_loc_set = CycleSubLocation.objects.filter(cycle=cycle_ref, sub_location__physical_location=physical_loc_ref, is_active=True)
    for cycle_sub_loc_ref in sub_loc_set:
        remove_sub_location_from_cycle(cycle_ref, cycle_sub_loc_ref.sub_location, curr_user)


def remove_sub_location_from_cycle(cycle_ref, sub_loc_ref, curr_user):
    # Implement the logic to remove the sub location from the cycle
    CycleSubLocation.objects.update_or_create(
        cycle=cycle_ref,
        sub_location=sub_loc_ref,
        defaults={"is_active": False, "updated_by": curr_user},
        create_defaults={
            "plant": cycle_ref.plant,
            "is_active": False,
            "created_by": curr_user,
            "updated_by": curr_user,
        },
    )
