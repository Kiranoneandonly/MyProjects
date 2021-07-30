from __future__ import unicode_literals
from shared.managers import CircusLookupManager, get_default_kwargs, CircusManager

MATCH_CATEGORIES = (
    ('new', 'New'),
    ('reps', 'Repetitions'),
    ('100', '100%'),
    ('95', '95%'),
    ('85', '85%'),
    ('75', '75%'),
    ('50', '50%'),
)

TRANSLATION_EDIT_PROOF_SERVICE_TYPE = 'tep'
TRANSLATION_ONLY_SERVICE_TYPE = 'translation'
PROOFREADING_SERVICE_TYPE = 'proof'
LINGUISTIC_QA_SERVICE_TYPE = 'linguistic_qa'
L10N_ENGINEERING_SERVICE_TYPE = 'l10n_engineering'
IMAGE_LOCALIZATION_SERVICE_TYPE = 'image_localization'
DTP_SERVICE_TYPE = 'dtp'
DTP_EDITS_SERVICE_TYPE = 'dtp_edits'
THIRD_PARTY_REVIEW_SERVICE_TYPE = 'third_party_review'
PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE = 'proof_third_party_review'
FINAL_APPROVAL_SERVICE_TYPE = 'final_approval'
POST_PROCESS_SERVICE_TYPE = 'post_process'
MT_POST_EDIT_SERVICE_TYPE = 'mt_pe'
GLOSSARY_DEVELOPMENT_SERVICE_TYPE = 'glossary_development'
GLOSSARY_EDITS_SERVICE_TYPE = 'glossary_edits'
OTHER_SERVICE_TYPE = 'other'
LINGUISTIC_TASK_SERVICE_TYPE = 'linguistic_task'
MINIMUM_FEE_SERVICE_TYPE = 'minimum_fee'
LINGUISTIC_SIGN_OFF_SERVICE_TYPE = 'lso'

CLIENT_REVIEW_SERVICE_TYPE = 'client_review'
CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE = 'client_review_bilingual_format'
CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE = 'client_review_final_product'

# LEGAL SERVICES
ACCESSIBILITY_SERVICE_TYPE = 'accessibility'
NOTARIZATION_SERVICE_TYPE = 'notarization'
ATTESTATION_SERVICE_TYPE = 'attestation'
ATTORNEY_REVIEW_SERVICE_TYPE = 'attorney_review'


# NON-WORKFLOW SERVICES
FEEDBACK_MANAGEMENT_SERVICE_TYPE = 'feedback_management'
FILE_PREP_SERVICE_TYPE = 'file_prep'
DISCOUNT_SERVICE_TYPE = 'client_discount'
RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE = 'recreate_of_pdf'
PM_SERVICE_TYPE = 'pm'
PM_HOUR_SERVICE_TYPE = 'pm_hour'

#Dummy Services
AUDIO_SERVICE_TYPE = 'audio'
ALPHA_SERVICE_TYPE = 'alpha'
BETA_SERVICE_TYPE = "beta"
GAMA_SERVICE_TYPE = 'gamma'
AUDIO_QA_SERVICE_TYPE = 'audio_qa'
ALPHA_QA_SERVICE_TYPE = 'alpha_qa'
BETA_QA_SERVICE_TYPE = 'beta_qa'
GAMA_QA_SERVICE_TYPE = 'gama_qa'

# code, description, translation_task, billable, jams_jobtaskID
SERVICE_TYPES = (
    (TRANSLATION_ONLY_SERVICE_TYPE, 'Translation Only', True, True, 1),
    (TRANSLATION_EDIT_PROOF_SERVICE_TYPE, 'Translation and Proofreading', True, True, 2),
    (PROOFREADING_SERVICE_TYPE, 'Proofreading Only', True, True, 3),
    (MT_POST_EDIT_SERVICE_TYPE, 'Post-MT editing', True, True, 48),
    (DTP_SERVICE_TYPE, 'Desktop Publishing', False, True, 4),
    (LINGUISTIC_SIGN_OFF_SERVICE_TYPE, 'Linguistic Sign Off', False, False, 49),
    (THIRD_PARTY_REVIEW_SERVICE_TYPE, 'Third Party Review', False, True, 5),
    (PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, 'Proofread/Review by 3rd party linguist', False, True, 5),
    (DTP_EDITS_SERVICE_TYPE, 'DTP Edits', False, True, 6),
    (CLIENT_REVIEW_SERVICE_TYPE, 'Client Review', False, False, 7),
    (CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE, 'Client Review (Bilingual Format)', False, False, 7),
    (CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE, 'Client Review (Final Product)', False, False, 7),
    (GLOSSARY_DEVELOPMENT_SERVICE_TYPE, 'Glossary Development', False, True, 8),
    (GLOSSARY_EDITS_SERVICE_TYPE, 'Glossary Edits', False, True, 9),
    (LINGUISTIC_QA_SERVICE_TYPE, 'Localization QA', False, True, 10),
    (OTHER_SERVICE_TYPE, 'Other', False, True, 11),
    (MINIMUM_FEE_SERVICE_TYPE, 'Minimum Fee', False, True, 13),
    (IMAGE_LOCALIZATION_SERVICE_TYPE, 'Image Localization', False, True, None),
    (L10N_ENGINEERING_SERVICE_TYPE, 'Engineering', False, True, 23),
    (ACCESSIBILITY_SERVICE_TYPE, 'Accessibility', False, True, None),
    (NOTARIZATION_SERVICE_TYPE, 'Notarization', False, True, 46),
    (ATTESTATION_SERVICE_TYPE, 'Attestation', False, True, 47),
    (ATTORNEY_REVIEW_SERVICE_TYPE, 'Attorney Review', False, True, 45),
    (PM_SERVICE_TYPE, 'Project Management', False, True, None),
    (PM_HOUR_SERVICE_TYPE, 'Project Management (Hour)', False, True, None),
    (FINAL_APPROVAL_SERVICE_TYPE, 'Final Approval', False, False, None),
    (POST_PROCESS_SERVICE_TYPE, 'Post Process', False, False, None),
    (AUDIO_SERVICE_TYPE, 'Audio', False, False, None),
    (ALPHA_SERVICE_TYPE, 'Alpha', False, False, None),
    (BETA_SERVICE_TYPE, 'Beta', False, False, None),
    (GAMA_SERVICE_TYPE, 'Gamma', False, False, None),
    (AUDIO_QA_SERVICE_TYPE, 'Audio QA', False, False, None),
    (ALPHA_QA_SERVICE_TYPE, 'Alpha QA', False, False, None),
    (BETA_QA_SERVICE_TYPE, 'Beta QA', False, False, None),
    (GAMA_QA_SERVICE_TYPE, 'Gama QA', False, False, None),
)

WORDS_UNITS = 'words'
HOURS_UNITS = 'hours'
FIXED_UNITS = 'fixed'
FILES_UNITS = 'files'
PERCENT_UNITS = 'percent'

UNITS = (
    (WORDS_UNITS, 'Words', None),
    # ('source', 'Source', 1),  NEED TO DYNAMICALLY PICK WHEN WORDS CHOSEN IN VTP AND PASSED JAMS API
    # ('target', 'Target', 2),  NEED TO DYNAMICALLY PICK WHEN WORDS CHOSEN IN VTP AND PASSED JAMS API
    (HOURS_UNITS, 'Hours', 3),
    ('minutes', 'Minutes', 12),
    ('pages', 'Pages', 5),
    ('screens', 'Screens', 13),
    ('formula', 'Formula', None),
    ('each', 'Each', None),
    (FILES_UNITS, 'Files', None),
    ('job', 'Job', None),
    (FIXED_UNITS, 'Fixed Fee', 6),
    ('na', 'N/A', 11),
    ('line', 'Line', 4),
)


service_units = {
    PM_SERVICE_TYPE: PERCENT_UNITS,
    DISCOUNT_SERVICE_TYPE: PERCENT_UNITS,
}


DOCUMENT_TYPES = (
    ('doc', 'DOC'),
    ('docx', 'DOCX'),
    ('dot', 'DOT'),
    ('txt', 'TXT'),
    ('xls', 'XLS'),
    ('xlsx', 'XLSX'),
    ('xlt', 'XLT'),
    ('htm', 'HTM'),
    ('html', 'HTML'),
    ('ppt', 'PPT'),
    ('pptx', 'PPTX'),
    ('pps', 'PPS'),
    ('csv', 'CSV'),
    ('rtf', 'RTF'),
    ('jsp', 'JSP'),
    ('asp', 'ASP'),
    ('aspx', 'ASPX'),
    ('inc', 'INC'),
    ('php', 'PHP'),
    ('pdf', 'PDF'),
    ('xml', 'XML'),
)

DEFAULT_INDUSTRY_CODE = 'default'
DEFAULT_SOURCE_LOCALE_DISPLAY = 'English - United States'
DEFAULT_SOURCE_LOCALE_CODE = 'English - United States'

INDUSTRIES = (
    (DEFAULT_INDUSTRY_CODE, 'Default'),
    ('auto', 'Automotive'),
    ('bank', 'Banking'),
    ('legal', 'Legal'),
    ('finance', 'Finance'),
    ('telecom', 'Telecommunications'),
    ('tech', 'High Tech'),
    ('pharma', 'Pharmaceuticals'),
    ('energy', 'Energy'),
    ('manufacturing', 'Manufacturing'),
    ('insurance', 'Insurance'),
    ('other', 'Other'),
    ('transport', 'Transportation'),
    ('services', 'Services'),
    ('government', 'Government'),
    ('education', 'Education'),
    ('healthcare', 'Healthcare'),
    ('public', 'Public interest'),
    ('marketing', 'Marketing'),
)

DEFAULT_VERTICAL_CODE = 'unassigned'
VERTICAL_UNASSIGNED = DEFAULT_VERTICAL_CODE
VERTICAL_CORPORATE = 'corporate'
VERTICAL_LEP = 'LEP'
VERTICAL_HEALTHCARE = 'healthcare'
VERTICAL_EDUCATION = 'education'
VERTICAL_LEGAL = 'legal'

VERTICALS = (
    (VERTICAL_UNASSIGNED, '_Unassigned'),
    (VERTICAL_CORPORATE, 'Corporate'),
    (VERTICAL_LEP, 'LEP'),
    # (VERTICAL_HEALTHCARE, 'Healthcare'),
    # (VERTICAL_EDUCATION, 'Education'),
    (VERTICAL_LEGAL, 'Legal'),
)

SOURCE_BASIS = 'words_source'
SOURCE_BASIS_TEXT = 'Source Words'
TARGET_BASIS = 'words_target'
TARGET_BASIS_TEXT = 'Target Words'

PRICING_BASIS = (
    (SOURCE_BASIS, SOURCE_BASIS_TEXT),
    (TARGET_BASIS, TARGET_BASIS_TEXT)
)

PRICING_SCHEMES_STANDARD = 'standard'
PRICING_SCHEMES_CORPORATE = 'corporate'
PRICING_SCHEMES_EDUCATION = 'education'
PRICING_SCHEMES_GOVERNMENT = 'government'
PRICING_SCHEMES_HEALTHCARE = 'healthcare'
PRICING_SCHEMES_HEALTHCARE_STRATEGIC = 'healthcare_strategic'
PRICING_SCHEMES_HEALTHCARE_PHI = 'healthcare_phi'
PRICING_SCHEMES_LEGAL = 'legal'
PRICING_SCHEMES_LEGAL_IP = 'legal_ip'
PRICING_SCHEMES_LEGAL_LITIGATION = 'litigation'
PRICING_SCHEMES_SOFTWARE = 'software'
PRICING_SCHEMES_LEARNING = 'learning'

PRICING_SCHEMES = (
    (PRICING_SCHEMES_STANDARD, 'Standard'),
    (PRICING_SCHEMES_CORPORATE, 'Corporate'),
    (PRICING_SCHEMES_EDUCATION, 'LEP:Education'),
    (PRICING_SCHEMES_HEALTHCARE, 'LEP:Healthcare'),
    (PRICING_SCHEMES_HEALTHCARE_STRATEGIC, 'LEP:Healthcare Strategic'),
    (PRICING_SCHEMES_HEALTHCARE_PHI, 'LEP:Healthcare PHI'),
    (PRICING_SCHEMES_LEGAL, 'Legal'),
    (PRICING_SCHEMES_LEGAL_IP, 'Legal IP'),
    (PRICING_SCHEMES_LEGAL_LITIGATION, 'Litigation'),
    (PRICING_SCHEMES_GOVERNMENT, 'Government'),
)


class ServiceTypeManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(SERVICE_TYPES))
        return obj

    def for_filter(self, filters):
        if 'service_type' in filters.keys():
            return self.filter(id=filters['service_type'])
        else:
            return self.get_empty_query_set()


class LocaleManager(CircusLookupManager):
    def default_source(self):
        obj, created = self.get_or_create(code='en', description='English')
        return obj

    def for_filter(self, filters, filter_name='source'):
        if filters.get(filter_name):
            id_list = filters.getlist(filter_name)
        else:
            id_list = [self.get_not_applicable().id]
        return self.filter(id__in=id_list)


class ScopeUnitManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(UNITS))
        return obj

    def for_filter(self, filters):
        if 'unit_of_measure' in filters.keys():
            return self.filter(id=filters['unit_of_measure'])
        else:
            return self.get_empty_query_set()


class IndustryManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(INDUSTRIES))
        return obj

    def for_filter(self, filters):
        try:
            return self.get(id=filters['industry'])
        except:
            return self.get_empty_query_set()


class VerticalManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(VERTICALS))
        return obj

    def for_filter(self, filters):
        try:
            return self.get(id=filters['vertical'])
        except:
            return self.get_empty_query_set()


class DocumentTypeManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(DOCUMENT_TYPES))
        return obj

    def for_filter(self, filters):
        try:
            return self.get(id=filters['document_type'])
        except:
            return self.get_empty_query_set()


class PricingBasisManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(PRICING_BASIS))
        return obj

    def for_filter(self, filters):
        try:
            return self.get(id=filters['pricing_basis'])
        except:
            return self.get_empty_query_set()


class PricingSchemeManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(PRICING_SCHEMES))
        return obj

    def for_filter(self, filters):
        try:
            return self.get(id=filters['pricing_scheme'])
        except:
            return self.get_empty_query_set()


class CountryManager(CircusLookupManager):
    def for_filter(self, filters):
        try:
            return self.get(id=filters['country'])
        except:
            return self.get_empty_query_set()
