import logging
from django.db.models import Q
from preferred_vendors.search_by_client import search_by_client
from services.managers import TRANSLATION_ONLY_SERVICE_TYPE, DTP_SERVICE_TYPE, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE
from services.models import ServiceType
from shared.managers import ManagerWithDefaultVertical

logger = logging.getLogger('circus.' + __name__)

class PreferredVendorManager(ManagerWithDefaultVertical):

    def top_vendor(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)

        try:
            candidates = self.vendors(
                vertical,
                client,
                source,
                target,
                service_type,
                phi_secure_client_job
            )

            candidates = candidates.order_by('client', 'priority')

            top_candidate = search_by_client(candidates, client=client, vertical=vertical)
            return top_candidate or None
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            logger.error(tb)
            logger.info('preferred_vendors.top_vendor(): ' + unicode(self))
            return None

    def vendors(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)

        try:
            candidates = self.filter(
                source=source, target=target, service_type=service_type
            ).filter(
                Q(client=client) | Q(client=client.parent) | Q(client=None)
            ).filter(
                Q(vertical=vertical) | Q(vertical=self.default_vertical_obj()) | Q(vertical_id=None)
            )

            if phi_secure_client_job:
                candidates = candidates.filter(vendor__vendor_manifest__is_phi_approved=True)

            candidates = candidates.order_by('client', 'vertical', 'priority')

            return candidates
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            logger.error(tb)
            logger.info('preferred_vendors.vendors(): ' + unicode(self))
            return None

    def tep_vendor(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
        return self.top_vendor(vertical, client, source, target, service_type, phi_secure_client_job)

    def translation_only_vendor(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=TRANSLATION_ONLY_SERVICE_TYPE)
        return self.top_vendor(vertical, client, source, target, service_type, phi_secure_client_job)

    def dtp_vendor(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=DTP_SERVICE_TYPE)
        return self.top_vendor(vertical, client, source, target, service_type, phi_secure_client_job)

    def review_vendor(self, vertical, client, source, target, service_type=None, phi_secure_client_job=None):
        if not service_type:
            service_type = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)
        return self.top_vendor(vertical, client, source, target, service_type, phi_secure_client_job)
