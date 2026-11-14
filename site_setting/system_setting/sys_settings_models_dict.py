from site_setting.system_setting.sys_settings_models_abs import SystemSettingBase


class VialTypeVolume(SystemSettingBase):
    name = "VIAL_TYPE_VOLUME_DICT"
    desc = "Vial Volume choices based on vial type"
    var_type = "dict_list"
    value = {
        "GLASS": ["40", "0", "17", "20", "35"],
        "DUCT": ["35"],
        "PAV": ["40"],
        "10mL HDPE": ["10"],
        "250mL HDPE": ["250", "4000"],
        "250mL HDPE, CL": ["250"],
        "Cleaned 30mL HD": ["35"],
        "Unclean 30mL HD": ["35"],
        "1L HDPE, CL": ["1100"],
        "SCHOTT": ["35"],
        "POLYSULFONE": ["35"],
    }

    def __init__(self):
        self._initialize()


class RoleAction(SystemSettingBase):
    name = "ROLE_ACTION"
    desc = "Role Actions from frontend"
    var_type = "dict_list"
    value = {
        "setting": ["Plant Setup", "PI Cycles", "Location", "Tag Range", "Counter & Data Entry"],
        "Book Inventary": ["PN List", "SAP Inventary", "Exclude PN List"],
        "Count": ["Tag / Manual Key-In", "Count Result Upload", "WMS Feed", "Virtual Tag Scan", "Count Results", "Pending Station"],
        "Audit": ["Audit Pending", "Audit Correction", "Audit Accuracy"],
        "Variance": ["Live Variance Report", "Variance by PN", "Variance by Location", "Post Batches"],
        "5-Day Update": ["Capture History", "5-Day Update", "Follow-up Register"],
        "Admin": [
            "Dropdown Management",
            "Notification Routing",
            "System Readiness",
            "User Management",
            "Bulk People Onboarding",
            "Role & Permissions",
            "Access History",
            "Database Administration",
        ],
    }

    def __init__(self):
        self._initialize()


# class FlaskVolUncert(SystemSettingBase):
#     name = "FLASK_VOLUME_UNCERT_DICT"
#     desc = "Flask uncertainty based on flask volume"
#     var_type = "dict_list"
#     value = {
#         "200": ["0"],
#         "250": ["0.00012"],
#         "500": ["0.0002"],
#         "1000": ["0.0003"],
#         "2000": ["0.0005"],
#         "4000": ["0.001"],
#         "6000": ["0.002"],
#     }

#     def __init__(self):
#         self._initialize()


# class VialQCProduct(SystemSettingBase):
#     name = "VIAL_QC_PRODUCT_DICT"
#     desc = "QC Instrument and product settings for Visual Assistant"
#     var_type = "dict_list"
#     value = {
#         "TOC_IC": ["TOC", "TC", "IC"],
#         "ACIDIFIED": ["TOC"],
#         "CONDUCTIVITY": ["CONDUCTIVITY"],
#         "N/A": ["N/A", "BORON", "ECLIPSE", "VIAL", "OBSOLETE"],
#     }

#     def __init__(self):
#         self._initialize()


# class ChemCOAPrepDict(SystemSettingBase):
#     name = "CHEM_COA_PREP_DICT"
#     desc = "Kit COA Prep dict"
#     var_type = "dict_text"
#     value = {
#         "QOI 917 00100 (sg.)": "This standard was prepared according to the method described in QOI 917 00100.",
#         "QOI 917 00100": "These standards were prepared according to the method described in QOI 917 00100.",
#         "QOI 917 00100 (acid)": "These standards were prepared according to the method described in QOI 917 00100. These standards are acidified to a pH of 3.0 S.U.",
#         "QOI 917 00100 (low IC)": "The inorganic carbon level of the low IC standard is determined from deionized water equilibrated with atmosphere CO2 at time of preparation.  These standards were prepared according to the method described in QOI 917 00100.",
#         "QOI 917 00100 & 00007 (acid)": "These standards were prepared according to the methods described in QOI 917 00100 and QOI 917 00007. These standards are acidified to a pH of 3.0 S.U.",
#         "QOI 917 35250": "This standard was prepared according to the method described in QOI 917 35250.",
#         "QOI 917 71002": "This standard was prepared according to the method described in QOI 917 71002.",
#         "QOI 800 10190": "This standard was prepared according to the method described in Worksheet 800 10190.",
#         "QOI 916 00007": "These standards were prepared according to the method described in QOI 916 00007.",
#         "QOI 917 00007": "This standard was prepared according to the method described in QOI 917 00007.",
#         "QOI 917 00010": "This standard was prepared according to the method described in QOI 917 00010.",
#         "QOI 917 78000": "These standards were prepared according to the method described in QOI 917 78000.",
#     }

#     def __init__(self):
#         self._initialize()


# class ChemCOAUsageDict(SystemSettingBase):
#     name = "CHEM_COA_USAGE_DICT"
#     desc = "Kit COA Usage dict"
#     var_type = "dict_text"
#     value = {
#         "USP-EP": "Suitable for US Pharmacopeia (USP) and European Pharmacopeia (EP) requirements on a maintained and calibrated instrument.",
#         "JP-KP": "Suitable for Japanese Pharmacopeia (JP) and Korean Pharmacopeia (KP) requirements on a maintained and calibrated instrument.",
#         "TOC": "Total Organic Carbon Analyzer Testing. ",
#         "Cond": "Conductivity Testing.",
#         "Rinse": "Rinse or flush solution.",
#         "Channel Rinse": "Channel Matching and Rinse Solution.",
#         "Boron": "Boron Measurements.",
#     }

#     def __init__(self):
#         self._initialize()


# class ChemCOAStorageDict(SystemSettingBase):
#     name = "CHEM_COA_STORAGE_DICT"
#     desc = "Kit COA Storage dict"
#     var_type = "dict_text"
#     value = {
#         "Room": "Store at room temperature.",
#         "No Freeze": "Store at room temperature.  Do not freeze. ",
#         "Refrigerator ": "Store at 5 ± 4°C ",
#     }

#     def __init__(self):
#         self._initialize()


# class ChemCOATraceDict(SystemSettingBase):
#     name = "CHEM_COA_TRACE_DICT"
#     desc = "Kit COA Trace dict"
#     var_type = "dict_text"
#     value = {
#         "Ver 1.": "Reference Materials are manufactured using equipment with calibrations traceable to the SI through national reference standards where manufactured. Carbon content of raw material for Total Organic Carbon (TOC) Certified Reference Material is traceable to third-party ISO 17025 accredited laboratory testing. Where applicable, raw material purity is traceable to national reference standard where manufactured.",
#         "Ver 2.": "Reference Materials are manufactured from direct USP source and using equipment with calibrations traceable to the SI through national reference standards where manufactured. Carbon content of raw material for Total Organic Carbon (TOC) Certified Reference Material is traceable to third-party ISO 17025 accredited laboratory testing. Where applicable, raw material purity is traceable to national reference standard where manufactured.",
#         "Ver 3.": "Manufacturers Certificate of Analysis",
#     }

#     def __init__(self):
#         self._initialize()


# class TestTextDict(SystemSettingBase):
#     name = "TEST_TEXT_DICT"
#     desc = "A Test dict for key value pairs"
#     var_type = "dict_text"
#     value = {
#         "GLASS": "Glass ware",
#         "DUCT": "30ml duct",
#     }

#     def __init__(self):
#         self._initialize()


# class ProductLineDict(SystemSettingBase):
#     name = "PRODUCT_LINE_DICT"
#     desc = "Part number and routing mapping dictionary"
#     var_type = "dict_list"
#     value = {"TOC IC": [], "High Cond": [], "Low Cond": []}

#     def __init__(self):
#         self._initialize()


# class VWLBoxDict(SystemSettingBase):
#     name = "VWL_BOX_DICT"
#     desc = "VWL Part Box capacity"
#     var_type = "dict_list"
#     value = {
#         "Blue": ["72", "30", "12"],
#         "White": ["72", "30"],
#         "Plastic": ["72"],
#         "Brown": ["72", "9"],
#         "Bag": ["72"],
#         "N/A": ["0", "9"],
#     }

#     def __init__(self):
#         self._initialize()


# class VWLVialDict(SystemSettingBase):
#     name = "VWL_VIAL_DICT"
#     desc = "VWL Part Vial Type"
#     var_type = "dict_list"
#     value = {
#         "Amber": ["40"],
#         "Duct": ["30"],
#         "Lab Duct": ["30"],
#         "Glass": ["40"],
#         "Lab Glass": ["40"],
#         "Cap": ["0"],
#         "N/A": ["0"],
#     }

#     def __init__(self):
#         self._initialize()


# class WeightMassTol(SystemSettingBase):
#     name = "WEIGHT_MASS_TOL_DICT"
#     desc = "Weight tolerance based on weight mass"
#     var_type = "dict_list"
#     value = {
#         "0.1": ["0.0005"],
#         "5": ["0.0005"],
#         "30": ["0.05"],
#         "500": ["0.5"],
#         "5000": ["5"],
#     }

#     def __init__(self):
#         self._initialize()


# class VialSampleQty(SystemSettingBase):
#     name = "VIAL_SAMPLE_QTY"
#     desc = "Sample Qty Need from overnight QC"
#     var_type = "dict_text"
#     value = {
#         "0": "No Sample Needed",
#         "1": "B, R1, R2",
#         "3": "B, R1, R2",
#         "4": "B, R1, R2, T8",
#         "5": "B, M, E, R1, R2",
#         "6": "B, M, E, R1, R2",
#         "30": "B, Every 30, R1, R2",
#         "50": "B, Every 50, R1, R2",
#     }

#     def __init__(self):
#         self._initialize()


# class VWLLabelPrinterDIct(SystemSettingBase):
#     name = "VWL_LABEL_PRINTER_Dict"
#     desc = "VWL Label Printer & Label Dict"
#     var_type = "dict_list"
#     value = {
#         "Zebra": ["Zebra"],
#         "Desktop": ["White", "Orange", "Yellow", "Light Blue"],
#         "N/A": ["N/A"],
#     }

#     def __init__(self):
#         self._initialize()


# class VialQCTypeDict(SystemSettingBase):
#     name = "VIAL_QC_TYPE_DICT"
#     desc = "Cons17025 QC Type List"
#     var_type = "dict_list"
#     value = {
#         "TOC": [
#             "0",
#             "STD 77100-01",
#             "STD 74000",
#             "STD 97701-01",
#             "STD 68100-01",
#             "STD 30024-02",
#             "STD 17001-01",
#             "STD 69100-01",
#             "STD 77501-02",
#         ],
#         "IC": ["0"],
#         "Cond": ["0"],
#         "PAV": ["0"],
#         "PBV": ["0"],
#         "0": ["0"],
#     }

#     def __init__(self):
#         self._initialize()


# class LocoChemEnumDict(SystemSettingBase):
#     name = "LOCO_CHEM_ENUM_DICT"
#     desc = "Loco Chem Enum for mobus"
#     var_type = "dict_text"
#     value = {
#         "0": "KCL",
#         "1": "HCL",
#     }

#     def __init__(self):
#         self._initialize()
