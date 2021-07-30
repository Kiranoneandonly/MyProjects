# -*- coding: utf-8 -*-
import logging
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAdminUser
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework.response import Response
from localization_kits.engine import analysis_from_json, analysis_failed_action, \
    kits_from_json, delivery_files_from_json
from projects.models import Project, BackgroundTask
from projects.tm_manager import _callback_update_tm
from shared.api_engine import STATUS_SUCCESS

logger = logging.getLogger('circus.' + __name__)


def bg_task_for_request(request):
    """
    :type request: rest_framework.request.Request
    :rtype: projects.models.BackgroundTask
    """

    bg_task = None
    bg_task_id = request.data.get('bg_task')

    if bg_task_id is not None:
        try:
            bg_task = BackgroundTask.objects.get(id=request.data['bg_task'])
        except BackgroundTask.DoesNotExist:
            logger.error("Bad background task ID %r", bg_task_id)

    return bg_task


class BadCallback(APIException):
    status_code = HTTP_400_BAD_REQUEST


class CallbackView(APIView):
    """Call this API endpoint to provide an answer to a BackgroundTask.

    Requests made with v2 of the DVX API in localization_kits.engine are
    responded to in one of these views.
    """

    permission_classes = (IsAdminUser,)

    def post(self, request):
        bg_task = bg_task_for_request(request)

        if not bg_task:
            raise BadCallback("no bg_task found")

        if bg_task.completed:
            logger.warning(u"API callback %r for %r but it was already completed at %s", self, bg_task, bg_task.completed)

        status = request.data.get('status')
        if int(status) != STATUS_SUCCESS:
            logger.warning(u"%s API POST received status %r:\n%r",
                         self, status, request.data, extra={'request': request})
            self.post_failure(request, bg_task)
            bg_task.errback(request.data)
            return Response({"status": 0})

        try:
            result = self.post_success(request, bg_task)
        except Exception, error:
            if not bg_task.errback(error):
                raise
        else:
            bg_task.callback(result)

        return Response({"status": 0})

    def post_success(self, request, bg_task):
        """Called on POST if the data indicates success.

        :type request: rest_framework.request.Request
        :type bg_task: projects.models.BackgroundTask
        :rtype: None
        """
        raise NotImplementedError("Subclass and override!")

    def post_failure(self, request, bg_task):
        """Called on POST if the data does not indicate success.

        :type request: rest_framework.request.Request
        :type bg_task: projects.models.BackgroundTask
        :rtype: None
        """
        pass


class Analysis(CallbackView):
    """Provide the results of an analysis."""

    def post_success(self, request, bg_task):
        project = Project.objects.select_related().get(id=(request.data['jobID']))

        try:
            return analysis_from_json(project.kit, request.data)
        except Exception:
            analysis_failed_action(project.kit)
            raise

    def post_failure(self, request, bg_task):
        project = Project.objects.select_related().get(id=(request.data['jobID']))
        analysis_failed_action(project.kit)


class PsuedoTranslate(CallbackView):

    def post_success(self, request, bg_task):
        # Nothing really to do here but kick off the callback.
        return None


class PreTranslation(CallbackView):
    # todo enter correct information about APIs
    """
    This text is the description for this API
    param1 -- A first parameter
    param2 -- A second parameter
    """

    def post_success(self, request, bg_task):
        # Nothing really to do here but kick off the callback.
        return None


class PreparedKit(CallbackView):
    """Provide files for Locale Translation Kits."""

    def post_success(self, request, bg_task):
        project = Project.objects.select_related().get(id=(request.data['jobID']))
        return kits_from_json(project.kit, request.data)


class TranslationImported(CallbackView):

    def post_success(self, request, bg_task):
        # Nothing really to do here but kick off the callback.
        return None


class DeliveryFiles(CallbackView):

    def post_success(self, request, bg_task):
        to_task = bg_task.task

        if not to_task:
            raise BadCallback("No Task identified for this delivery.")

        return delivery_files_from_json(to_task.id, request.data)


class QACheck(CallbackView):

    def post_success(self, request, bg_task):
        # Nothing really to do here but kick off the callback.
        return None


class AddToTM(CallbackView):

    def post_success(self, request, bg_task):
        project = Project.objects.select_related().get(id=(request.data['jobID']))
        return _callback_update_tm(project.kit)


class AddToTB(CallbackView):

    def post_success(self, request, bg_task):
        # Nothing really to do here but kick off the callback.
        # project = Project.objects.select_related().get(id=(request.data['jobID']))
        return None
