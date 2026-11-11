from site_setting.system_setting.sys_settings_models_abs import SystemSettingBase


class VarianceSummaryGrouping(SystemSettingBase):
    name = "PLANT_VAR_SUM_DEFAULT"
    desc = "Plant.variance_summary_default"
    var_type = "list"
    value = ["SAP_LOCATION", "BUSINESS_UNIT", "OWNERSHIP"]

    def __init__(self):
        self._initialize()


class BusinessRole(SystemSettingBase):
    name = "BUSINESS_ROLE"
    desc = "Business Roles"
    var_type = "list"
    value = ["Global Admin", "Plant Admin", "Data Entry", "Varience Viewer", "Varience Approver", "CM"]

    def __init__(self):
        self._initialize()


class SAPInventoryType(SystemSettingBase):
    name = "SAP_INVENTORY_TYPE"
    desc = "SAP Inventory Type for SAP Location"
    var_type = "list"
    value = ["FII_OWNED", "CONSIGNED"]

    def __init__(self):
        self._initialize()


class SAPEntryMethod(SystemSettingBase):
    name = "SAP_ENTRY_METHOD"
    desc = "SAP Entry Method for SAP Location"
    var_type = "list"
    value = ["WMS Feed", "Tag / Manual Key-in", "Count Upload", "Virtual Tag Scan"]

    def __init__(self):
        self._initialize()


class BusinessOptionCategory(SystemSettingBase):
    name = "BUSINESS_OPTION_CATEGORY"
    desc = "Business Option Category for Business Option"
    var_type = "list"
    value = ["ROOT_CAUSE", "SAP_CORRECTION_TYPE"]

    def __init__(self):
        self._initialize()


class Departments(SystemSettingBase):
    name = "DEPARTMENTS"
    desc = "Departments for the Plant"
    var_type = "list"
    value = ["Warehouse", "Production", "MRB", "Finish Goods"]

    def __init__(self):
        self._initialize()


class CycleStatus(SystemSettingBase):
    name = "CYCLE_STATUS"
    desc = "Cycle Status for the Plant"
    var_type = "list"
    value = ["DRAFT", "OPEN", "CLOSED", "VOID"]

    def __init__(self):
        self._initialize()


class OnboardingStatus(SystemSettingBase):
    name = "ONBOARDING_STATUS"
    desc = "Onboadring Status"
    var_type = "list"
    value = ["PREVIEW", "IMPORTED", "FAILED"]

    def __init__(self):
        self._initialize()


class CountSource(SystemSettingBase):
    name = "COUNT_SOURCE"
    desc = "Count Source"
    var_type = "list"
    value = ["WMS Feed", "Count Upload", "Tag Key-in", "Manual Key-in", "Virtual Tag Scan"]

    def __init__(self):
        self._initialize()


class ExceptionStatus(SystemSettingBase):
    name = "COUNT_EXCEPTION_STATUS"
    desc = "Count: Exception Status"
    var_type = "list"
    value = ["Pending", "Approved New Part", "Mapped to Existing Part", "Rejected"]

    def __init__(self):
        self._initialize()
