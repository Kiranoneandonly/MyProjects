from django.conf.urls import url
from localization_kits import views as v
from localization_kits import authorization as authz

urlpatterns = []

via_only_urls = authz.any_via_user.protect_patterns(
    # FileAnalysis
    url(r'^assets/(?P<pk>\d+)/edit/$', v.AnalysisUpdateView.as_view(), name='kits_asset_analysis_edit'),
    url(r'^assets/(?P<pk>\d+)/$', v.AnalysisDetailView.as_view(), name='kits_asset_analysis'),

    # LocaleTranslationKit
    url(r'^download/ltk_file/(?P<pk>\d+)/?$', v.localetranslationkit_file_download_handler, name='download_localetranslationkit_translation_file'),
    url(r'^queue_analysis/(?P<loc_kit_id>\d+)/?$', v.queue_analysis, name='queue_analysis'),

    # ajax
    url(r'^ajax/analysis_status/?$', v.via_check_analysis_status, name='via_check_analysis_status'),
)
urlpatterns.extend(via_only_urls)


urlpatterns.extend(authz.project_owners.protect_patterns(
    # LocalizationKit
    # CSRF
    url(r'^p_(?P<proj_id>\d+)/upload_file/$', v.upload_file_to_kit, name='kit_upload_file'),
))

urlpatterns.extend(authz.project_viewers.protect_patterns(
    # FileAsset
    # Used by: clients, vendors, VIA
    url(r'^download/p_(?P<proj_id>\d+)/asset/(?P<asset_id>\d+)/?$', v.asset_download_handler, name='download_asset'),
))

urlpatterns.extend(authz.protected_task.protect_patterns(
    # TaskLocaleTranslationKit
    # Used by: VIA & vendors (as Task.files)
    url(r'^download/t_(?P<task_id>\d+)/tltk_infile/(?P<tltk_id>\d+)/?$', v.tasklocaletranslationkit_infile_download_handler, name='download_tasklocaletranslationkit_in_file'),
    url(r'^download/t_(?P<task_id>\d+)/tltk_outfile/(?P<tltk_id>\d+)/?$', v.tasklocaletranslationkit_outfile_download_handler, name='download_tasklocaletranslationkit_out_file'),
    url(r'^download/t_(?P<task_id>\d+)/tltk_supfile/(?P<tltk_id>\d+)/?$', v.tasklocaletranslationkit_supfile_download_handler, name='download_tasklocaletranslationkit_sup_file'),
    url(r'^download/t_(?P<task_id>\d+)/tltk_tmfile/(?P<tltk_id>\d+)/?$', v.tasklocaletranslationkit_tmfile_download_handler, name='download_tasklocaletranslationkit_tm_file'),

    # TaskLocalizedAsset
    # Used by: VIA & vendors (as Task.files)
    url(r'^download/t_(?P<task_id>\d+)/tla_infile/(?P<tla_id>\d+)/?$', v.tasklocalizedasset_infile_download_handler, name='download_tasklocalizedasset_in_file'),
    # Final delivery to the client is also a TLA.
    url(r'^download/t_(?P<task_id>\d+)/tla_outfile/(?P<tla_id>\d+)/?$', v.tasklocalizedasset_outfile_download_handler, name='download_tasklocalizedasset_out_file'),
    url(r'^download/t_(?P<task_id>\d+)/tla_supfile/(?P<tla_id>\d+)/?$', v.tasklocalizedasset_supfile_download_handler, name='download_tasklocalizedasset_sup_file'),
    url(r'^download/t_(?P<task_id>\d+)/tla_post_deliveryfile/(?P<tla_id>\d+)/?$', v.tasklocalizedasset_post_deliveryfile_download_handler, name='download_tasklocalizedasset_post_delivery_file'),
))
