from site_setting.system_setting.sys_settings_models_abs import SystemSettingBase


class IsLocal(SystemSettingBase):
    name = "IS_LOCAL"
    desc = "Not Running on Server"
    var_type = "bool"
    value = True

    def __init__(self):
        self._initialize()


# class FullTestServer(SystemSettingBase):
#     name = "FULL_TEST"
#     desc = "Test Server Print Real Label"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class SyncTestMfe(SystemSettingBase):
#     name = "SYNC_TEST_MFE"
#     desc = "Sync with TestMFE DB when Data is modified in MES"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class DualDbSync(SystemSettingBase):
#     name = "DUAL_DB_SYNC"
#     desc = "Sync with MFE DB when Data is modified in MES"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class DebugMode(SystemSettingBase):
#     name = "DEBUG_MODE"
#     desc = "Print Out additional debug info in MES"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class VesselHourCheck(SystemSettingBase):
#     name = "VESSEL_HOUR_CHECK"
#     desc = "Check Vessel Hour for operators"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class DigitalCoaEnabled(SystemSettingBase):
#     name = "DIGITAL_COA_ENABLED"
#     desc = "Enable digital COA barcode on labels"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class WeighEachCrystal(SystemSettingBase):
#     name = "WEIGHT_EACH_CRYSTAL"
#     desc = "Weigh every crystal container when filling Clean Acid"
#     var_type = "bool"
#     value = True

#     def __init__(self):
#         self._initialize()


# class UserAuthorizedAppOnly(SystemSettingBase):
#     name = "USER_AUTHORIZED_APP_ONLY"
#     desc = "User Can ONLY Access Authorized Apps"
#     var_type = "bool"
#     value = False

#     def __init__(self):
#         self._initialize()
