import os
import uuid

from django.core.exceptions import BadRequest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from web_page.models import File

ATTACHMENTS_DIR = "storage\\files"
IMAGE_DIR = "storage\\files\\images"


def load_attachment(request):
    if request.GET['restore'] is not None:
        file_obj: File = get_object_or_404(File, id=int(request.GET['restore']))

        return HttpResponse(headers={
            'Content-Disposition': f'inline; filename="{file_obj.file_name};"'
        })

    return BadRequest("Ошибка удаления привязки")


def remove_attachment(request):
    file = get_object_or_404(File, id=int(request.body.decode('utf-8')))
    default_storage.delete(file.path)
    file.delete()

    return HttpResponse(None)


def upload_attachment(request):
    file = request.FILES.getlist("attachments")[0]
    file_obj: File = File(path="None", file_name=file.name)
    file_obj.save()
    file_obj.path = f"{ATTACHMENTS_DIR}\\{file_obj.id}"
    default_storage.save(file_obj.path, ContentFile(file.read()))
    file_obj.save()

    return HttpResponse(file_obj.id)


def upload_image(request):
    file = request.FILES.getlist("file")[0]

    guid = uuid.uuid4()
    _, extentions = os.path.splitext(file.name)

    path = f"{IMAGE_DIR}\\{guid}{extentions}"
    default_storage.save(path, ContentFile(file.read()))
    url = reverse('get_image', kwargs={"name": f"{guid}{extentions}"})

    return HttpResponse(f"{{ \"link\": \"{url}\" }}")


def get_image(request, name: str):
    path = f"{IMAGE_DIR}\\{name}"
    file = default_storage.open(path)

    return HttpResponse(file)
