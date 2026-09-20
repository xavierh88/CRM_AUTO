"""Local document path resolution without application startup dependencies."""

from pathlib import Path


def resolve_document_path(reference: str, upload_root: Path) -> Path | None:
    """Resolve local references only; upload_root must be administrator-controlled.

    No basename fallback: an invalid reference must not select another document.
    Symlinks are rejected before probing their targets. This does not replace
    authorization or protect against concurrent filesystem changes during open.
    """
    if not isinstance(reference, str) or not reference or "\x00" in reference:
        return None
    root = Path(upload_root).absolute()
    if reference.startswith('/uploads/'):
        reference = reference[len('/uploads/'):]
    path = Path(reference)
    if '..' in path.parts:
        return None
    try:
        relative = path.relative_to(root) if path.is_absolute() else path
    except ValueError:
        return None
    candidate = root / relative
    try:
        # Check ancestors as well: a configured root must not redirect elsewhere.
        current = Path(root.anchor)
        for part in candidate.parts[1:]:
            current = current / part
            if current.is_symlink():
                return None
        return candidate if candidate.is_file() else None
    except OSError:
        return None
