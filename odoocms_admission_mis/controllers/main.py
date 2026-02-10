import base64
import io
import zipfile
from odoo import http
from odoo.http import request, Response
from werkzeug.utils import secure_filename
import mimetypes
from PIL import Image



class DownloadController(http.Controller):

    @http.route('/download/export_applicant_images', type='http', auth='user', methods=['GET'], csrf=False)
    def export_applicant_images(self, record_ids, **kwargs):
        """
        Generate a ZIP file containing images from selected odoocms.application records.
        The `record_ids` parameter should be a comma-separated list of record IDs.
        """
        try:
            record_ids = [int(x) for x in record_ids.split(',')]
        except Exception:
            return Response("Invalid record_ids parameter.", status=400)
        records = request.env['odoocms.application'].sudo().with_context(prefetch_fields=False).browse(record_ids)
        if not records:
            return Response("No valid records found.", status=404)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for rec in records:
                try:
                    # Verify field exists before accessing
                    if 'image' not in rec._fields:
                        continue
                    img_field = rec.image
                    app_no = rec.application_no
                except Exception:
                    continue

                if img_field and app_no:
                    try:
                        image_data = base64.b64decode(img_field)
                    except Exception:
                        continue 
                    file_name = secure_filename(f"{app_no}.jpg")
                    zip_file.writestr(file_name, image_data)

        zip_buffer.seek(0)
        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', 'attachment; filename="exported_applicant_images.zip"'),
        ]
        return Response(zip_buffer.getvalue(), headers=headers)


    @http.route('/download/export_applicant_all_documents', type='http', auth='user', methods=['GET'], csrf=False)
    def export_applicant_all_documents(self, record_ids, **kwargs):
        """
        Export all binary fields from selected application records.
        Each record gets its own folder named after `application_no`.
        Fields are verified to exist before accessing to avoid KeyError.
        """
        try:
            record_ids = [int(x) for x in record_ids.split(',')]
        except Exception:
            return Response("Invalid record_ids parameter.", status=400)

        records = request.env['odoocms.application'].sudo().with_context(prefetch_fields=False).browse(record_ids)
        if not records:
            return Response("No valid records found.", status=404)

        # Profile fields - only include fields that exist in CMU model
        # These are verified to exist: image, cnic_front, cnic_back, domicile, pass_port
        profile_fields = ['image', 'cnic_front', 'domicile', 'cnic_back', 'pass_port']
        
        # Academic fields - verified: attachment, hope_certificate (transcript doesn't exist in CMU)
        academic_fields = ['attachment', 'hope_certificate']

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for rec in records:
                folder_name = secure_filename(rec.application_no or f"record_{rec.id}")

                # Profile fields - verify each field exists before accessing
                for field in profile_fields:
                    # CRITICAL: Check if field exists in model to avoid KeyError
                    if field not in rec._fields:
                        continue

                    try:
                        file_data = rec[field]
                    except (KeyError, AttributeError):
                        continue
                    
                    if not file_data:
                        continue

                    decoded_data = self._safe_decode(file_data)
                    if not decoded_data:
                        continue

                    ext = self._guess_extension(decoded_data)
                    if ext:
                        file_name = f"{field}{ext}"
                        zip_path = f"{folder_name}/{secure_filename(file_name)}"
                        zip_file.writestr(zip_path, decoded_data)

                # Academic fields - verify each field exists before accessing
                academic_records = request.env['applicant.academic.detail'].sudo().search(
                    [('application_id', '=', rec.id)]
                )
                if academic_records:
                    for idx, academic_rec in enumerate(academic_records, start=1):
                        for field in academic_fields:
                            # CRITICAL: Check if field exists in academic model to avoid KeyError
                            if field not in academic_rec._fields:
                                continue

                            try:
                                file_data = academic_rec[field]
                            except (KeyError, AttributeError):
                                continue
                            
                            if not file_data:
                                continue

                            decoded_data = self._safe_decode(file_data)
                            if not decoded_data:
                                continue

                            ext = self._guess_extension(decoded_data)
                            if ext:
                                file_name = f"academic_{idx}_{field}{ext}"
                                zip_path = f"{folder_name}/{secure_filename(file_name)}"
                                zip_file.writestr(zip_path, decoded_data)

        zip_buffer.seek(0)
        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', 'attachment; filename="exported_applicant_files.zip"'),
        ]
        return Response(zip_buffer.getvalue(), headers=headers)

    def _safe_decode(self, b64data):
        try:
            return base64.b64decode(b64data)
        except Exception:
            return None

    def _guess_extension(self, data):
        file_ext = None

        if data.startswith(b"\xff\xd8\xff") and not file_ext:
            file_ext = ".jpg"
            return ".jpg"
        elif data.startswith(b"\x89PNG") and not file_ext:
            file_ext = ".png"
            return ".png"
        elif data.startswith(b"%PDF") and not file_ext:
            file_ext = ".pdf"
            return ".pdf"
        elif data.startswith(b"PK") and not file_ext:
            file_ext = ".docx"
            return ".docx"
        elif not file_ext:
            try:
                img = Image.open(io.BytesIO(data))
                img.load()
                format_ext = img.format.lower()
                file_ext = f".{format_ext}"
                return file_ext
            except Exception:
                pass
        
        # fallback: detect with mimetypes if possible
        if not file_ext:
            mime_type = mimetypes.guess_type("dummy")[0]
            if mime_type:
                file_ext = mimetypes.guess_extension(mime_type) or ".bin"
            else:
                file_ext = ".bin"
        return file_ext

