from __future__ import unicode_literals

import cStringIO as StringIO
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.template import Context
from django.http import StreamingHttpResponse
from tasks.models import VendorPurchaseOrder


def render_to_pdf(template_src, context_dict):
    # FIXME: pisa is not currently an installed requirement!
    # also ho.pisa has been succeeded by xhtml2pdf.pisa http://www.xhtml2pdf.com
    import ho.pisa as pisa
    template = get_template(template_src)
    context = Context(context_dict)
    html = template.render(context)
    result = StringIO.StringIO()

    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return StreamingHttpResponse(result.getvalue(), mimetype='application/pdf')


def vendor_po(request, pk=None):
    po = get_object_or_404(VendorPurchaseOrder, pk=pk)
    context = {
        'pagesize': 'A4',
        'po': po,
    }
    return render(request=request, template_name='shared/finance/vendor_po.html', context=context)


def vendor_po_preview(request, pk=None):
    po = get_object_or_404(VendorPurchaseOrder, pk=pk)
    context = {
        'pagesize': 'A4',
        'po': po,
    }
    return render(request=request, template_name='shared/finance/vendor_po.html', context=context)
