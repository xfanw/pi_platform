from site_setting.system_setting.sys_settings_models_abs import SystemSettingBase


class PrinterURL(SystemSettingBase):
    name = "PRINTER_URL"
    desc = "Bartender Server URL"
    var_type = "text"
    value = "test_url"

    def __init__(self):
        self._initialize()


# class COAShareRoot(SystemSettingBase):
#     name = "COA_SHARE_ROOT"
#     desc = "Mounted share drive root for COA output"
#     var_type = "text"
#     value = "/mnt/z_drive"

#     def __init__(self):
#         self._initialize()


# class COAShareSubdir(SystemSettingBase):
#     name = "COA_SHARE_SUBDIR"
#     desc = "COA Folder (default: Operations/Consumables)"
#     var_type = "text"
#     value = "Operations/Consumables"

#     def __init__(self):
#         self._initialize()


# class FirstShiftStart(SystemSettingBase):
#     name = "FIRST_SHIFT_START"
#     desc = "First Shift Start time"
#     var_type = "time"
#     value = "07:00"

#     def __init__(self):
#         self._initialize()


# class BoronSpectrophotometer(SystemSettingBase):
#     name = "BORON_SPECTROPHOTOMETER"
#     desc = "Boron Spectrophotometer TMF"
#     var_type = "text"
#     value = "TMF 70777"

#     def __init__(self):
#         self._initialize()


# class VWLCapMeanDiff(SystemSettingBase):
#     name = "VWL_CAP_MEAN_DIFF"
#     desc = "VWL Caps Hypothesized Mean Difference"
#     var_type = "text"
#     value = "10"

#     def __init__(self):
#         self._initialize()


# class VWLCapLimit(SystemSettingBase):
#     name = "VWL_CAP_LIMIT"
#     desc = "VWL Caps Pass Val"
#     var_type = "text"
#     value = "0.05"

#     def __init__(self):
#         self._initialize()


# class ServerType(SystemSettingBase):
#     name = "SERVER_TYPE"
#     desc = "Server Type (PROD/TEST)"
#     var_type = "text"
#     value = "PROD"

#     def __init__(self):
#         self._initialize()
