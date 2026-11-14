from site_setting.models import SystemSetting


class SystemSettingBase(object):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls._instances.get(cls, None) is None:
            cls._instances[cls] = super(SystemSettingBase, cls).__new__(cls, *args, **kwargs)
        return SystemSettingBase._instances[cls]

    def _initialize(self):
        db_ref = self.search_db()
        if not db_ref:
            if self.var_type == "bool":
                self._set_bool("System Init")
            else:
                self._set_text("System Init")

    def _set_bool(self, user_name):
        try:
            SystemSetting.objects.update_or_create(var_name=self.name, defaults={"var_status": self.value, "updater": user_name})
        except:
            pass

    def _set_text(self, user_name):
        try:
            SystemSetting.objects.update_or_create(var_name=self.name, defaults={"var_text": self.value, "updater": user_name})
        except:
            pass

    def search_db(self):
        try:
            return SystemSetting.objects.filter(var_name=self.name).first()
        except:
            return None

    def refresh_from_db(self):
        db_ref = self.search_db()
        if self.var_type == "bool":
            self.value = db_ref.var_status if db_ref else self.value
        elif self.var_type in ["list", "dict_list", "dict_text"]:
            self.value = eval(db_ref.var_text) if db_ref else self.value
        else:
            self.value = db_ref.var_text if db_ref else self.value

    def set(self, value, user_name):
        if self.var_type == "bool":
            if value == "true":
                self.value = True
            if value == "false":
                self.value = False
            self._set_bool(user_name)
        else:
            self.value = value
            self._set_text(user_name)

    # for list values
    def remove_val(self, var_value, user_name):
        self.value.remove(var_value)
        self._set_text(user_name)

    def add_val(self, var_value, user_name):
        self.value.append(var_value)
        self._set_text(user_name)

    # for dict keys
    def remove_key(self, key, user_name):
        self.value.pop(key)
        self._set_text(user_name)

    def add_key(self, key, user_name):
        if self.var_type == "dict_list":
            new_pair = {key: []}
        else:
            new_pair = {key: ""}
        self.value.update(new_pair)
        self._set_text(user_name)

    # for dict values
    def remove_key_val(self, curr_key, curr_value, user_name):
        self.value.get(curr_key).remove(curr_value)
        self._set_text(user_name)

    def add_key_val(self, curr_key, curr_value, user_name):
        self.value.get(curr_key).append(curr_value)
        self._set_text(user_name)

    def update_key_val(self, curr_key, curr_value, user_name):
        self.value.update({curr_key: curr_value})
        self._set_text(user_name)


class FakeValue(SystemSettingBase):
    name = "FAKE_VALUE"
    desc = "ERROR ON THIS LINE, Contact PI_MES team"
    var_type = "text"
    value = "error"

    def set(self, *args, **kwargs):
        # Immutable class
        pass

    def refresh_from_db(self):
        # Immutable class
        pass
