import mimetypes
from django.conf import settings
from django.utils.module_loading import import_module
# from django.utils.importlib import import_module

PREPARE_UPLOAD_BACKEND = getattr(settings, 'PREPARE_UPLOAD_BACKEND', 'filetransfers.backends.default.prepare_upload')
SERVE_FILE_BACKEND = getattr(settings, 'SERVE_FILE_BACKEND', 'filetransfers.backends.default.serve_file')
PUBLIC_DOWNLOAD_URL_BACKEND = getattr(settings, 'PUBLIC_DOWNLOAD_URL_BACKEND', 'filetransfers.backends.default.public_download_url')

_backends_cache = {}

##############
# Public API
##############


def prepare_upload(request, url, private=False, backend=None):
    handler = _load_backend(backend, PREPARE_UPLOAD_BACKEND)
    return handler(request, url, private=private)


def serve_file(request, file, backend=None, save_as=False, content_type=None):
    # Backends are responsible for handling range requests.
    handler = _load_backend(backend, SERVE_FILE_BACKEND)
    filename = file.name.rsplit('/')[-1]
    if save_as is True:
        save_as = filename
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0]
    response = handler(request, file, save_as=save_as, content_type=content_type)

#    # An abortive attempt to make filenames in firefox preserve spaces
#    # get the content_disposition_header
#    location_header = response._headers['location']
#    parsed_header = urlparse.urlparse(location_header[1])
#    qs = urlparse.parse_qs(parsed_header.query)
#    content_disp = qs['response-content-disposition']
#
#    # modify the content_disposition_header
#    param_begin = content_disp[0].find('filename="') + len('filename="')
#    #content_disp[0] = content_disp[0].replace('%20', '+')
#    #content_disp[0] = content_disp[0][:param_begin] + '%quot' + content_disp[0][param_begin:-1] + '%quot' + content_disp[0][-1]
#    #content_disp[0] = content_disp[0][:param_begin] + content_disp[0][param_begin:-1] + content_disp[0][-1]
#
#    # add the modified content_disposition back to response
#    # convert from tuple
#    parsed_header = list(parsed_header)
#    parsed_header[4]= urllib.urlencode(qs)
#    response._headers['location'] = (location_header[0], urlparse.urlunparse(parsed_header))
#    import ipdb; ipdb.set_trace()

    return response


def public_download_url(file, backend=None):
    handler = _load_backend(backend, PUBLIC_DOWNLOAD_URL_BACKEND)
    return handler(file)


# Internal utilities
def _load_backend(backend, default_backend):
    if backend is None:
        backend = default_backend
    if backend not in _backends_cache:
        module_name, func_name = backend.rsplit('.', 1)
        _backends_cache[backend] = getattr(import_module(module_name), func_name)
    return _backends_cache[backend]
