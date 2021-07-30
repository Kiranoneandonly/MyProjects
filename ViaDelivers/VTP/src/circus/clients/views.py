from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView, CreateView

from clients.forms import ClientForm, ClientManifestForm, NoteForm
from clients.models import Client, ClientManifest


class ClientsListView(ListView):
    template_name = "via/clients/list.html"

    def get_queryset(self):
        return Client.objects.all().order_by('name').select_related('manifest').prefetch_related('parent')

    def get_context_data(self, **kwargs):
        context = super(ClientsListView, self).get_context_data(**kwargs)
        return context


class ClientDetailView(DetailView):
    template_name = "via/clients/detail.html"
    queryset = Client.objects.all()
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super(ClientDetailView, self).get_context_data(**kwargs)
        return context


class ClientCreateView(CreateView):
    template_name = "via/clients/create.html"
    form_class = ClientForm
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super(ClientCreateView, self).get_context_data(**kwargs)
        return context


def update(request, client_id):
    template = "via/clients/edit.html"
    client = get_object_or_404(Client, id=client_id)
    manifest = client.manifest
    if request.method == 'POST':
        account_form = ClientForm(data=request.POST, instance=client, prefix='account')
        manifest_form = ClientManifestForm(data=request.POST, instance=manifest, prefix='manifest')

        all_valid = account_form.is_valid() and manifest_form.is_valid()

        if all_valid:
            account_form.save()
            manifest_form.save()
            messages.success(request, "Client information saved.")
    else:
        account_form = ClientForm(instance=client, prefix='account')
        manifest_form = ClientManifestForm(instance=manifest, prefix='manifest')

    context = {
        'client': client,
        'account_form': account_form,
        'manifest_form': manifest_form,
    }
    return render(request=request, template_name=template, context=context)


def edit_note(request, client_id):
    template = "via/clients/note.html"
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        form = NoteForm(request.POST)

        if form.is_valid():
            manifest = client.manifest
            if client.parent:
                parent_manifest = ClientManifest.objects.get(client=client.parent)
            else:
                parent_manifest = None

            manifest.note = form.cleaned_data['note']
            manifest.save()

            if parent_manifest:
                parent_manifest.note = form.cleaned_data['parent_note']
                parent_manifest.save()

            messages.success(request, "Note saved.")
            return redirect('clients_note', client.id)
    else:
        form = NoteForm.for_client(client)

    context = {
        'client_name': client.name,
        'parent_name': client.parent.name if client.parent else None,
        'client': client,
        'note_form': form,
    }
    return render(request=request, template_name=template, context=context)
