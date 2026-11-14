from site_setting.system_setting.sys_settings_models_abs import FakeValue
from site_setting.system_setting.sys_settings_models_bool import *
from site_setting.system_setting.sys_settings_models_database import *
from site_setting.system_setting.sys_settings_models_dict import *
from site_setting.system_setting.sys_settings_models_list import *
from site_setting.system_setting.sys_settings_models_text import *
from log.models import SystemSettingLog


class SysSet(object):

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(SysSet, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        # NULL Object
        self.FAKE_VALUE = FakeValue()

        # Switches
        # self.SERVER_TYPE = ServerType()
        self.IS_LOCAL = IsLocal()

        # Texts
        self.PRINTER_URL = PrinterURL()
        # self.FIRST_SHIFT_START = FirstShiftStart()

        # Lists
        self.PLANT_VAR_SUM_DEFAULT = VarianceSummaryGrouping()
        self.BUSINESS_ROLE = BusinessRole()
        self.SAP_INVENTORY_TYPE = SAPInventoryType()
        self.SAP_ENTRY_METHOD = SAPEntryMethod()
        self.BUSINESS_OPTION_CATEGORY = BusinessOptionCategory()
        self.DEPARTMENTS = Departments()
        self.CYCLE_STATUS = CycleStatus()
        self.ONBOARDING_STATUS = OnboardingStatus()
        self.COUNT_SOURCE = CountSource()
        self.COUNT_EXCEPTION_STATUS = ExceptionStatus()

        # Dicts
        self.VIAL_TYPE_VOLUME_DICT = VialTypeVolume()

        # MFE DB Setup
        self.MFE_DB_HOST = MfeDbHost()
        # self.MFE_DB_USER = MfeDbUser()
        # self.MFE_DB_PASSWORD = MfeDbPassword()

        # self.STD_QC_DB_HOST = StdQCDbHost()
        # self.STD_QC_DB_DBNAME = StdQCDbName()
        # self.STD_QC_DB_USER = StdQCDbUser()
        # self.STD_QC_DB_PASSWORD = StdQCDbPassword()

        # self.VWL_DB_HOST = VwlDbHost()
        # self.VWL_DB_DBNAME = VwlDbName()
        # self.VWL_DB_USER = VwlDbUser()
        # self.VWL_DB_PASSWORD = VwlDbPassword()

        # self.LOCAL_MFE_DB_HOST = LocalMfeDbHost()
        # self.LOCAL_MFE_DB_USER = LocalMfeDbUser()
        # self.LOCAL_MFE_DB_PASSWORD = LocalMfeDbPassword()

        # self.ORDER_QUERY_RANGE = OrderQueryRange()

    def get_obj(self, var_name):
        try:
            obj_ref = getattr(self, var_name)
            obj_ref.refresh_from_db()  # this line is to resolve multithreading issues, deserve a better solution
            return obj_ref
        except Exception as e:
            print(e)
            return self.FAKE_VALUE

    def get_val(self, var_name):
        try:
            obj_ref = getattr(self, var_name)
            obj_ref.refresh_from_db()  # this line is to resolve multithreading issues, deserve a better solution
            return obj_ref.value
        except:
            return self.FAKE_VALUE.value

    def set_obj(self, var_name, var_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f"{var_obj.value} --> {var_value}")
                var_obj.set(var_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")

    def delete_list_val(self, var_name, var_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f"{var_obj.value} --> Remove {var_value}")
                var_obj.refresh_from_db()
                var_obj.remove_val(var_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")

    def add_list_val(self, var_name, var_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f"{var_obj.value} --> Add {var_value}")

                var_obj.refresh_from_db()
                var_obj.add_val(var_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {var_value}")

    def delete_dict_key(self, var_name, curr_key, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f"{var_obj.value.get(curr_key)} --> Remove Key {curr_key}")
                var_obj.refresh_from_db()
                var_obj.remove_key(curr_key, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")

    def add_dict_key(self, var_name, curr_key, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f"{var_obj.value.get(curr_key)}--> Add Key {curr_key}")

                var_obj.refresh_from_db()
                var_obj.add_key(curr_key, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")

    def delete_dict_value(self, var_name, curr_key, curr_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")
            else:
                SystemSettingLog.create_log(
                    var_obj.name, user_name, f"{curr_key}:{var_obj.value.get(curr_key)} --> Remove Value {curr_value}"
                )
                var_obj.refresh_from_db()
                var_obj.remove_key_val(curr_key, curr_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}")

    def add_dict_value(self, var_name, curr_key, curr_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")
            else:
                SystemSettingLog.create_log(
                    var_obj.name, user_name, f"{curr_key}:{var_obj.value.get(curr_key)} --> Add Value{curr_value}"
                )

                var_obj.refresh_from_db()
                var_obj.add_key_val(curr_key, curr_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")

    def edit_dict_key_value(self, var_name, curr_key, curr_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")
            else:
                SystemSettingLog.create_log(
                    var_obj.name,
                    user_name,
                    f"{curr_key}:{var_obj.value.get(curr_key)} --> Edit Key Value {curr_value}",
                )

                var_obj.refresh_from_db()
                var_obj.update_key_val(curr_key, curr_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")

    def add_dict_key_value(self, var_name, curr_key, curr_value, user_name):
        try:
            var_obj = getattr(self, var_name)
            if var_obj is self.FAKE_VALUE:
                SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")
            else:
                SystemSettingLog.create_log(var_obj.name, user_name, f" Add Key Value {curr_key}:{curr_value}")

                var_obj.refresh_from_db()
                var_obj.update_key_val(curr_key, curr_value, user_name)
        except:
            SystemSettingLog.create_log("Error Action", user_name, f"{var_name}: {curr_key}:{curr_value}")
