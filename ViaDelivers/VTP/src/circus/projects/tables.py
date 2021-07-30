from django_tables2 import tables, RequestConfig, LinkColumn
from django_tables2.utils import A
from projects.models import Project


class ProjectTableConfig(RequestConfig):
    def configure(self, table):
        """
        Filter the table before sort and paginate
        """
        filter = self.request.GET.getlist('filter')


        return super(ProjectTableConfig, self).configure(table)


class ProjectTable(tables.Table):
    job_number = LinkColumn('via_job_detail_overview', args=[A('id')])

    class Meta:
        template = 'shared/components/table.html'
        attrs = {'class': 'table table-bordered table-striped'}
        model = Project
        fields = ('status', 'client', 'job_number', 'name')
        order_by = ('status', 'client', 'job_number')
