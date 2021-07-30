from django.conf.urls import url
import dwh_reports.views as v


urlpatterns = [

    url(r'^task_completion_velocity/?$', v.task_completion_velocity, name='task_completion_velocity_supplier'),
    url(r'^supplier_ratings_by_task/?$', v.supplier_ratings_by_task, name='supplier_ratings_by_task'),
    url(r'^supplier_ratings_by_task_detail/(?P<assignee_id>\d+)/(?P<start>(\d{4})-(\d{2})-(\d+))/(?P<end>(\d{4})-(\d{2})-(\d+))/?$', v.SupplierTasksRating.as_view(), name='supplier_ratings_by_task_detail'),
    url(r'^supplier_ratings_by_task_details_csv_export/(?P<assignee_id>\d+)/(?P<days>\d+)/?$', v.supplier_ratings_by_task_details_csv_export, name='supplier_ratings_by_task_details_csv_export'),

]