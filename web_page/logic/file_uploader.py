import os
import uuid
import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import BadRequest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from web_page.models import File
from web_page.utils import for_teacher

ATTACHMENTS_DIR = os.path.join("storage", "files")
IMAGE_DIR = os.path.join("storage", "files", "images")


@login_required
@for_teacher()
def load_attachment(request):
    if request.GET['restore'] is not None:
        file_obj: File = get_object_or_404(File, id=int(request.GET['restore']))

        return HttpResponse(headers={
            'Content-Disposition': f'inline; filename="{file_obj.file_name};"'
        })

    return BadRequest("Ошибка удаления привязки")


@login_required
@for_teacher()
def remove_attachment(request):
    file = get_object_or_404(File, id=int(request.body.decode('utf-8')))
    default_storage.delete(file.path)
    file.delete()

    return HttpResponse(None)


@login_required
@for_teacher()
def upload_attachment(request):
    file = request.FILES.getlist("attachments")[0]
    file_obj: File = File(path="None", file_name=file.name)
    file_obj.save()
    file_obj.path = os.path.join(ATTACHMENTS_DIR, str(file_obj.id))
    default_storage.save(file_obj.path, ContentFile(file.read()))
    file_obj.save()

    return HttpResponse(file_obj.id)


@login_required
@for_teacher()
def upload_image(request):
    file = request.FILES.getlist("file")[0]

    guid = uuid.uuid4()
    _, extentions = os.path.splitext(file.name)

    path = os.path.join(IMAGE_DIR, f"{guid}{extentions}")
    default_storage.save(path, ContentFile(file.read()))
    url = reverse('get_image', kwargs={"name": f"{guid}{extentions}"})

    return HttpResponse(f"{{ \"link\": \"{url}\" }}")


@login_required
@for_teacher()
def get_image(request, name: str):
    path = os.path.join(IMAGE_DIR, name)
    file = default_storage.open(path)

    return HttpResponse(file)


@login_required
@for_teacher()
def get_file(request, file_id: int):
    path = os.path.join(ATTACHMENTS_DIR, str(file_id))
    file = default_storage.open(path)
    return HttpResponse(file)
