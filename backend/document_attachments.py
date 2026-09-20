"""Local attachment selection only; this module never sends communications."""

from pathlib import Path
import re

from document_paths import resolve_document_path


DOCUMENT_FIELDS = (
    ("id_documents", "id_file_url", "ID"),
    ("income_documents", "income_proof_file_url", "Ingresos"),
    ("residence_documents", "residence_proof_file_url", "Residencia"),
)


def collect_document_attachments(client: dict, cosigners: list, upload_root: Path) -> list:
    """Select confined existing files from current and legacy document metadata.

    Authorization belongs to the caller. Deduplicate within each person so legacy
    metadata does not repeat a current document, while retaining cosigner labels.
    Names are sanitized for MIME headers; original document paths are never logged.
    """
    attachments = []
    people = [(client, f"{client.get('first_name', 'Cliente')}_{client.get('last_name', '')}")]
    for index, cosigner in enumerate(cosigners, 1):
        info = cosigner.get("info") if isinstance(cosigner, dict) else None
        if isinstance(info, dict):
            people.append((info, f"CoSigner{index}_{info.get('first_name', '')}"))

    for person, name in people:
        safe_name = re.sub(r"[^\w-]", "_", name)[:100]
        seen = set()
        for array_field, legacy_field, label in DOCUMENT_FIELDS:
            documents = person.get(array_field)
            documents = documents if isinstance(documents, list) else []
            references = [
                (doc.get("path") or doc.get("file_path"), f"_{index}" if len(documents) > 1 else "")
                for index, doc in enumerate(documents, 1) if isinstance(doc, dict)
            ]
            references.append((person.get(legacy_field), ""))
            for reference, suffix in references:
                path = resolve_document_path(reference, upload_root)
                if path is None or path in seen:
                    continue
                seen.add(path)
                safe_extension = re.sub(r"[^a-zA-Z0-9.]", "_", path.suffix)[:20]
                attachments.append({
                    "path": str(path),
                    "name": f"{safe_name}_{label}{suffix}{safe_extension}",
                })
    return attachments
