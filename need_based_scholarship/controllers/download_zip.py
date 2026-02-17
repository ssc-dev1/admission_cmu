# controllers/download_zip.py  (or append to your existing controller file)

import base64
import io
import re
import zipfile
import mimetypes

from odoo import http
from odoo.http import request

_SAFE_RE = re.compile(r'[^A-Za-z0-9_.\-]+')

# Magic byte signatures for common file types
# Format: (magic_bytes, offset, extension, mime_type)
FILE_SIGNATURES = [
    # PDF
    (b'%PDF', 0, '.pdf', 'application/pdf'),
    # Images
    (b'\x89PNG\r\n\x1a\n', 0, '.png', 'image/png'),
    (b'\xff\xd8\xff', 0, '.jpg', 'image/jpeg'),
    (b'GIF87a', 0, '.gif', 'image/gif'),
    (b'GIF89a', 0, '.gif', 'image/gif'),
    (b'RIFF', 0, '.webp', 'image/webp'),  # WebP (check for WEBP later)
    (b'BM', 0, '.bmp', 'image/bmp'),
    # Microsoft Office (older .doc, .xls, .ppt)
    (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 0, '.doc', 'application/msword'),
    # ZIP-based formats (docx, xlsx, pptx, odt, etc.) - detected as zip first
    (b'PK\x03\x04', 0, '.zip', 'application/zip'),
    # Plain text / HTML
    (b'<!DOCTYPE', 0, '.html', 'text/html'),
    (b'<html', 0, '.html', 'text/html'),
    (b'<?xml', 0, '.xml', 'application/xml'),
    # Archives
    (b'\x1f\x8b', 0, '.gz', 'application/gzip'),
    (b'Rar!\x1a\x07', 0, '.rar', 'application/x-rar-compressed'),
    (b'7z\xbc\xaf\x27\x1c', 0, '.7z', 'application/x-7z-compressed'),
]


def _detect_file_type(data):
    """
    Detect file type from binary content using magic bytes.
    Returns (extension, mime_type) tuple.
    Falls back to '.bin' if unknown.
    """
    if not data or len(data) < 8:
        return '.bin', 'application/octet-stream'
    
    for magic, offset, ext, mime in FILE_SIGNATURES:
        if data[offset:offset + len(magic)] == magic:
            # Special handling for ZIP-based formats (Office docs, ODT, etc.)
            if ext == '.zip' and len(data) > 30:
                # Check for Office Open XML formats
                try:
                    import zipfile as zf
                    from io import BytesIO
                    with zf.ZipFile(BytesIO(data), 'r') as z:
                        names = z.namelist()
                        if '[Content_Types].xml' in names:
                            if any('word/' in n for n in names):
                                return '.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                            elif any('xl/' in n for n in names):
                                return '.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            elif any('ppt/' in n for n in names):
                                return '.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                        elif 'mimetype' in names:
                            # OpenDocument formats
                            mimetype = z.read('mimetype').decode('utf-8', errors='ignore').strip()
                            if 'opendocument.text' in mimetype:
                                return '.odt', mimetype
                            elif 'opendocument.spreadsheet' in mimetype:
                                return '.ods', mimetype
                            elif 'opendocument.presentation' in mimetype:
                                return '.odp', mimetype
                except Exception:
                    pass
                return ext, mime
            
            # Special handling for WebP (RIFF header but needs WEBP check)
            if ext == '.webp':
                if len(data) >= 12 and data[8:12] == b'WEBP':
                    return '.webp', 'image/webp'
                # Not WebP, could be WAV or other RIFF format
                if len(data) >= 12 and data[8:12] == b'WAVE':
                    return '.wav', 'audio/wav'
                continue
            
            return ext, mime
    
    # Fallback: try to guess if it looks like text
    try:
        sample = data[:1000]
        sample.decode('utf-8')
        # If it decodes as UTF-8, it's likely text
        if b'<' in sample and b'>' in sample:
            return '.html', 'text/html'
        return '.txt', 'text/plain'
    except Exception:
        pass
    
    return '.bin', 'application/octet-stream'


def _safe_name(name, fallback='file'):
    if not name:
        return fallback
    return _SAFE_RE.sub('_', name)


def _to_bytes(data):
    """Accepts base64 string/bytes and returns raw bytes. Returns None if empty."""
    if not data:
        return None
    if isinstance(data, bytes):
        # could be raw bytes or base64 in bytes; try decode, else keep as-is
        try:
            return base64.b64decode(data)
        except Exception:
            return data
    if isinstance(data, str):
        # handle data URI or plain b64
        payload = data.split(',')[-1]
        return base64.b64decode(payload)
    return None


def _filename_from_model_field(rec, field_name, default_base, file_data=None):
    """
    Generate a proper filename for a binary field.
    
    Priority:
    1. Use '<field>_fname' if it exists and has a value
    2. Detect file type from content and use proper extension
    3. Fall back to default_base with .bin extension
    """
    fname_field = f'{field_name}_fname'
    if fname_field in rec._fields:
        val = rec[fname_field]
        if val:
            return _safe_name(val)
    
    # Detect file type from content
    if file_data:
        ext, _ = _detect_file_type(file_data)
        # Build filename: field_name_recordid + detected extension
        base_name = f'{field_name}_{rec.id}'
        return _safe_name(base_name) + ext
    
    return _safe_name(default_base)


class NeedBasedScholarshipAdminZip(http.Controller):

    @http.route('/nbs/admin/download_zip/<int:rec_id>',
                type='http', auth='user', methods=['GET'], csrf=False)
    def download_zip(self, rec_id, **kwargs):
        """
        Streams a ZIP of:
          - all ir.attachment rows bound to this NBS record
          - all binary fields on the main NBS record
          - all binary fields on O2M child rows
        """
        # ensure the user can read the record
        env = request.env
        NBS = env['need.based.scholarship']
        try:
            NBS.check_access_rights('read')
        except Exception:
            return request.not_found()

        rec = NBS.browse(rec_id).exists()
        if not rec:
            return request.not_found()
        try:
            rec.check_access_rule('read')
        except Exception:
            return request.not_found()

        # Build ZIP
        out = io.BytesIO()
        z = zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED)

        # 0) chatter/linked attachments
        att_domain = [('res_model', '=', 'need.based.scholarship'), ('res_id', '=', rec.id)]
        for att in env['ir.attachment'].sudo().search(att_domain):
            if not att.datas:
                continue
            content = _to_bytes(att.datas) or b''
            # Use original attachment name if available, otherwise detect from content
            if att.name and '.' in att.name:
                name = _safe_name(att.name)
            elif hasattr(att, 'datas_fname') and att.datas_fname and '.' in att.datas_fname:
                name = _safe_name(att.datas_fname)
            else:
                # Detect file type from content
                ext, _ = _detect_file_type(content)
                name = _safe_name(f'attachment_{att.id}') + ext
            z.writestr(f'00_ir_attachments/{name}', content)

        # 1) binaries on main record
        for field_name, field in rec._fields.items():
            if field.type != 'binary':
                continue
            data = rec.sudo()[field_name]
            if not data:
                continue
            # Convert to bytes first so we can detect file type
            content = _to_bytes(data) or b''
            fname = _filename_from_model_field(rec, field_name, f'{field_name}_{rec.id}.bin', file_data=content)
            z.writestr(f'01_main/{fname}', content)

        # 2) binaries on O2M children (all O2M fields, all their binary fields)
        for o2m_name, o2m_field in rec._fields.items():
            if o2m_field.type != 'one2many':
                continue
            lines = rec.sudo()[o2m_name]
            if not lines:
                continue

            for line in lines:
                # Make a stable folder name per line
                label = ''
                if 'name' in line._fields and line.name:
                    label = f'_{_safe_name(str(line.name))}'
                folder = f'02_lines/{o2m_name}/{line.id}{label}'

                for lf_name, lf in line._fields.items():
                    if lf.type != 'binary':
                        continue
                    ldata = line.sudo()[lf_name]
                    if not ldata:
                        continue
                    # Convert to bytes first so we can detect file type
                    content = _to_bytes(ldata) or b''
                    pretty = _filename_from_model_field(line, lf_name, f'{lf_name}_{line.id}.bin', file_data=content)
                    z.writestr(f'{folder}/{pretty}', content)

        z.close()

        # If archive ended empty, include a README
        if not out.getvalue():
            with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z2:
                z2.writestr('README.txt', b'No attachments or binary uploads were found on this record.')

        # Prepare response
        label = _safe_name(rec.registration_number or rec.full_name or f'NBS_{rec.id}')
        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', f'attachment; filename="{label}_attachments.zip"'),
        ]
        return request.make_response(out.getvalue(), headers)
