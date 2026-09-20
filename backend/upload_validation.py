"""Bounded document reads and server-generated, non-symlink upload paths."""
from pathlib import Path
import re
from fastapi import HTTPException

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BATCH_BYTES = 25 * 1024 * 1024
MAX_FILES = 5
TYPES = {'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}


async def bounded_read(file, limit=MAX_FILE_BYTES):
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, 'Upload exceeds size limit')
    if not data:
        raise HTTPException(400, 'Empty upload')
    return data


def safe_filename(name):
    if (not isinstance(name, str) or not name or len(name) > 200 or name in {'.', '..'}
            or any(ord(char) < 32 for char in name) or '/' in name or '\\' in name):
        raise HTTPException(400, 'Invalid upload filename')
    return name


async def validate_documents(files):
    if not 1 <= len(files) <= MAX_FILES:
        raise HTTPException(400, 'Upload between one and five documents')
    validated, total = [], 0
    for file in files:
        name = safe_filename(file.filename)
        ext = name.rsplit('.', 1)[-1].lower()
        if ext not in TYPES or file.content_type != TYPES[ext]:
            raise HTTPException(415, 'Only PDF, PNG and JPEG documents are supported')
        data = await bounded_read(file)
        total += len(data)
        if total > MAX_BATCH_BYTES:
            raise HTTPException(413, 'Upload batch exceeds size limit')
        valid = ((ext == 'pdf' and data.startswith(b'%PDF-')) or
                 (ext == 'png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or
                 (ext in {'jpg', 'jpeg'} and data.startswith(b'\xff\xd8\xff')))
        if not valid:
            raise HTTPException(415, 'Document content does not match its type')
        validated.append({'filename': name, 'extension': ext, 'type': TYPES[ext], 'content': data})
    return validated


def upload_directory(root, client_id):
    if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', client_id):
        raise HTTPException(400, 'Invalid client path')
    path = Path(root).absolute() / 'clients' / client_id
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise HTTPException(400, 'Symlink upload paths are not allowed')
    return path


async def validate_import(file):
    """Validate bounded tabular imports before pandas parses them."""
    import io
    import zipfile
    name = safe_filename(file.filename)
    ext = name.rsplit('.', 1)[-1].lower()
    mime = file.content_type
    allowed = {'csv': {'text/csv', 'application/csv', 'application/vnd.ms-excel'},
               'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
               'xls': {'application/vnd.ms-excel'}}
    if ext not in allowed or mime not in allowed[ext]:
        raise HTTPException(415, 'Unsupported import file type')
    data = await bounded_read(file)
    if ext == 'csv':
        try:
            text = data.decode('utf-8-sig')
        except UnicodeError:
            raise HTTPException(415, 'CSV must contain UTF-8 text')
        if '\x00' in text:
            raise HTTPException(415, 'Invalid CSV content')
    elif ext == 'xls':
        if not data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            raise HTTPException(415, 'Invalid Excel content')
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = archive.infolist()
                if (len(members) > 1000 or sum(x.file_size for x in members) > MAX_BATCH_BYTES
                        or any(x.flag_bits & 1 for x in members)):
                    raise HTTPException(413, 'Expanded spreadsheet exceeds limits')
                if not {'[Content_Types].xml', 'xl/workbook.xml'} <= set(archive.namelist()):
                    raise HTTPException(415, 'Invalid Excel content')
        except zipfile.BadZipFile:
            raise HTTPException(415, 'Invalid Excel content')
    return data
