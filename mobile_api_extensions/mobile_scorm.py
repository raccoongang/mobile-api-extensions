import logging
import time
import os
import shutil

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files import File

from openedxscorm.scormxblock import parse_validate_positive_float, ScormXBlock
from xblock.fields import Scope, String
from xblock.core import XBlock


log = logging.getLogger(__name__)
SCORM_ROOT = os.path.join(settings.MEDIA_ROOT, 'scorm')


def _(text):
    return text


class MobileScormXBlock(ScormXBlock):
    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Mobile Scorm",
        scope=Scope.settings,
    )

    @XBlock.supports("multi_device")
    def student_view(self, context=None):
        return super().student_view(context)

    @XBlock.handler
    def studio_submit(self, request, _suffix):
        response = super().studio_submit(request, _suffix)
        if hasattr(request.params['file'], 'file'):
            self.create_zip_file(request.params['file'].file)
        return response

    def publish_grade(self, set_last_updated_time=True):
        if set_last_updated_time:
            self.scorm_data['last_updated_time'] = int(time.time())
        self.runtime.publish(
            self,
            "grade",
            {"value": self.get_grade(), "max_value": self.weight},
        )

    def set_value(self, data, set_last_updated_time=True):
        name = data.get("name")
        value = data.get("value")
        completion_percent = None
        success_status = None
        completion_status = None
        lesson_score = None

        self.scorm_data[name] = value
        if name == "cmi.core.lesson_status":
            lesson_status = data.get("value")
            if lesson_status in ["passed", "failed"]:
                success_status = lesson_status
            elif lesson_status in ["completed", "incomplete"]:
                completion_status = lesson_status
        elif name == "cmi.success_status":
            success_status = value
        elif name == "cmi.completion_status":
            completion_status = value
        elif name in ["cmi.core.score.raw", "cmi.score.raw"] and self.has_score:
            lesson_score = parse_validate_positive_float(value, name) / 100.0
        elif name == "cmi.progress_measure":
            completion_percent = parse_validate_positive_float(value, name)

        context = {"result": "success"}
        if lesson_score is not None:
            self.lesson_score = lesson_score
            context.update({"grade": self.get_grade()})
            if self.has_score:
                self.publish_grade(set_last_updated_time)
        if completion_percent is not None:
            self.emit_completion(completion_percent)
        if completion_status:
            self.lesson_status = completion_status
            context.update({"completion_status": completion_status})
        if success_status:
            self.success_status = success_status
        if completion_status == "completed":
            self.emit_completion(1)
        if success_status or completion_status == "completed":
            if self.has_score:
                self.publish_grade(set_last_updated_time)

        return context

    @XBlock.json_handler
    def scorm_get_values(self, data, suffix=''):
        return self.scorm_data

    @XBlock.json_handler
    def scorm_set_values(self, data, _suffix):
        is_updated = False
        if isinstance(data, dict):
            if self.scorm_data.get('last_updated_time', 0) < data.get('last_updated_time', 0):
                for datum in data.get('data'):
                    self.set_value(datum, set_last_updated_time=False)
                self.scorm_data['last_updated_time'] = int(data.get('last_updated_time', 0))
                is_updated = True
            context = self.scorm_data
            context.update({"is_updated": is_updated})
            return context
        else:
            return [self.set_value(data) for data in data]

    def student_view_data(self):
        """
        Inform REST api clients about original file location and it's "freshness".
        Make sure to include `student_view_data=openedxscorm` to URL params in the request.

        Note: we are not sure what this view is for and it might be removed in the future.
        """
        if self.index_page_url:
            scorm_data = default_storage.url(self._file_storage_path())
            if not scorm_data.startswith('http'):
                scorm_data = '{}{}'.format(settings.LMS_ROOT_URL, scorm_data)

            return {
                "last_modified": self.package_meta.get("last_updated", ""),
                "size": self.package_meta.get("size", 0),
                "index_page": self.index_page_path,
                'scorm_data': scorm_data,
            }
        return {}

    def _file_storage_path(self):
        """
        Get file path of storage.
        """
        path = (
            '{loc.org}/{loc.course}/{loc.block_type}/{loc.block_id}'
            '/{sha1}{ext}'.format(
                loc=self.location,
                sha1=self.package_meta['sha1'],
                ext=os.path.splitext(self.package_meta['name'])[1]
            )
        )
        return path

    def create_zip_file(self, scorm_file):
        path = self._file_storage_path()

        if default_storage.exists(path):
            log.info('Removing previously uploaded "{}"'.format(path))
            default_storage.delete(path)

        default_storage.save(path, File(scorm_file))
        log.info('"{}" file stored at "{}"'.format(scorm_file, path))

        # Check whether SCORM_ROOT exists
        if not os.path.exists(SCORM_ROOT):
            os.mkdir(SCORM_ROOT)

        # Now unpack it into SCORM_ROOT to serve to students later
        path_to_file = os.path.join(SCORM_ROOT, self.location.block_id)

        if os.path.exists(path_to_file):
            shutil.rmtree(path_to_file)

        if hasattr(scorm_file, 'temporary_file_path'):
            os.system('unzip {} -d {}'.format(scorm_file.temporary_file_path(), path_to_file))
        else:
            temporary_path = os.path.join(SCORM_ROOT, scorm_file.name)
            temporary_zip = open(temporary_path, 'wb')
            scorm_file.open()
            temporary_zip.write(scorm_file.read())
            temporary_zip.close()
            os.system('unzip {} -d {}'.format(temporary_path, path_to_file))
            os.remove(temporary_path)
