# -*- coding: utf-8 -*-
from django.conf.urls import url
import api_views as v

# haven't tested how Django REST Framework's auth stuff plays with Protector,
# so leaving authorization in the hands of restframework.permissions for now.

urlpatterns = [
                       url(r'^analysis$', v.Analysis.as_view(), name='api_analysis'),
                       url(r'^pretranslate$', v.PreTranslation.as_view(), name='api_pretrans'),
                       url(r'^psuedotranslate$', v.PsuedoTranslate.as_view(), name='psuedotranslate'),
                       url(r'^prepared_kit$', v.PreparedKit.as_view(), name='api_prep_kit'),
                       url(r'^translation_imported$', v.TranslationImported.as_view(), name='api_translation_imported'),
                       url(r'^qa_check$', v.QACheck.as_view(), name='qa_check'),
                       url(r'^delivery_files$', v.DeliveryFiles.as_view(), name='delivery_files'),
                       url(r'^add_to_tm$', v.AddToTM.as_view(), name='add_to_tm'),
                       url(r'^add_to_tb$', v.AddToTB.as_view(), name='add_to_tb'),
                       ]
