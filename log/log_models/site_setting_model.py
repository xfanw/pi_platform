from log.log_models.abstract_model import *


# Sievers MES Setting Log
class SystemSettingLog(UserActionDateMemo):
    # memo old -> new
    # action var_name
    @staticmethod
    def create_log(action, user_name, memo):
        SystemSettingLog.objects.create(action=action, user=user_name, memo=memo)
