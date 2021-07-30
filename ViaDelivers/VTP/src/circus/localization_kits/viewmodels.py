# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe

from services.models import DocumentType


class LocalizationKitForAnalysis(object):
    def __init__(self, loc_kit):
        """
        :type loc_kit: localization_kits.models.LocalizationKit
        """
        self.loc_kit = loc_kit

    @property
    def blockers(self):
        return self.doctype_blockers + self.locale_blockers


    @cached_property
    def doctype_blockers(self):
        blockers = []
        for asset in self.loc_kit.source_files():
            if asset.prepared_name:
                which = u'Prepared'
                name = asset.prepared_name
            else:
                which = u'Source'
                name = asset.orig_name

            doctype = name.rsplit('.', 1)[-1].strip().lower()
            auto_estimate_doctype = DocumentType.objects.filter(
                code=doctype, can_semiauto_estimate=True)
            if not auto_estimate_doctype.exists():
                msg = (u"%s file <span class='filename'>%s</span>: "
                       u"extension <code class='file_ext'>%s</code> "
                       u"not supported." % (
                           which, escape(name), escape(doctype)))

                msg = mark_safe(msg)
                blockers.append(msg)

        return blockers


    @cached_property
    def locale_blockers(self):
        blockers = []
        project = self.loc_kit.project

        target_locales = project.target_locales.all()
        if len(target_locales) > settings.LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE:
            blockers.append(u"%s targets is too many (%s max)." % (
                len(target_locales),
                settings.LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE))

        return blockers
