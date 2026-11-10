from site_setting.system_setting.sys_settings_models_abs import SystemSettingBase


# MFE DB Settings
class MfeDbHost(SystemSettingBase):
    name = "MFE_DB_HOST"
    desc = "MFE DB host"
    var_type = "text"
    value = "localhost"

    def __init__(self):
        self._initialize()


# class MfeDbUser(SystemSettingBase):
#     name = "MFE_DB_USER"
#     desc = "MFE DB Username"
#     var_type = "text"
#     value = "root"

#     def __init__(self):
#         self._initialize()


# class MfeDbPassword(SystemSettingBase):
#     name = "MFE_DB_PASSWORD"
#     desc = "MFE DB Password"
#     var_type = "text"
#     value = "TestPassword"

#     def __init__(self):
#         self._initialize()


# # Standard QC DB Settings
# class StdQCDbHost(SystemSettingBase):
#     name = "STD_QC_DB_HOST"
#     desc = "STD QC DB Host"
#     var_type = "text"
#     value = "W03600009BD7DS2\DPLSERVER"

#     def __init__(self):
#         self._initialize()


# class StdQCDbName(SystemSettingBase):
#     name = "STD_QC_DB_DBNAME"
#     desc = "STD QC DB name"
#     var_type = "text"
#     value = "dpldb"

#     def __init__(self):
#         self._initialize()


# class StdQCDbUser(SystemSettingBase):
#     name = "STD_QC_DB_USER"
#     desc = "STD QC DB User"
#     var_type = "text"
#     value = "readOnly"

#     def __init__(self):
#         self._initialize()


# class StdQCDbPassword(SystemSettingBase):
#     name = "STD_QC_DB_PASSWORD"
#     desc = "STD QC DB Password"
#     var_type = "text"
#     value = "1234!@#$qwer"

#     def __init__(self):
#         self._initialize()


# # Vial Wash DB Settings
# class VwlDbHost(SystemSettingBase):
#     name = "VWL_DB_HOST"
#     desc = "VWL DB Host"
#     var_type = "text"
#     value = "W0360000C2PQ1S2\DPLSERVER19"

#     def __init__(self):
#         self._initialize()


# class VwlDbName(SystemSettingBase):
#     name = "VWL_DB_DBNAME"
#     desc = "VWL DB name"
#     var_type = "text"
#     value = "dpldb"

#     def __init__(self):
#         self._initialize()


# class VwlDbUser(SystemSettingBase):
#     name = "VWL_DB_USER"
#     desc = "VWL DB User"
#     var_type = "text"
#     value = "readOnly"

#     def __init__(self):
#         self._initialize()


# class VwlDbPassword(SystemSettingBase):
#     name = "VWL_DB_PASSWORD"
#     desc = "VWL DB Password"
#     var_type = "text"
#     value = "1234!@#$qwer"

#     def __init__(self):
#         self._initialize()


# # Local MFE DB Settings
# class LocalMfeDbHost(SystemSettingBase):
#     name = "LOCAL_MFE_DB_HOST"
#     desc = "Local MFE DB host"
#     var_type = "text"
#     value = "localhost"

#     def __init__(self):
#         self._initialize()


# class LocalMfeDbUser(SystemSettingBase):
#     name = "LOCAL_MFE_DB_USER"
#     desc = "Local MFE DB Username"
#     var_type = "text"
#     value = "root"

#     def __init__(self):
#         self._initialize()


# class LocalMfeDbPassword(SystemSettingBase):
#     name = "LOCAL_MFE_DB_PASSWORD"
#     desc = "Local MFE DB Password"
#     var_type = "text"
#     value = "TestPassword"

#     def __init__(self):
#         self._initialize()


# class OrderQueryRange(SystemSettingBase):
#     name = "ORDER_QUERY_RANGE"
#     desc = "Default planning order querying range"
#     var_type = "text"
#     value = "90"

#     def __init__(self):
#         self._initialize()


# class CartStdUsageRange(SystemSettingBase):
#     name = "CART_STD_USAGE_RANGE"
#     desc = "Cartridge available lot no lookup range in days"
#     var_type = "text"
#     value = "21"

#     def __init__(self):
#         self._initialize()
