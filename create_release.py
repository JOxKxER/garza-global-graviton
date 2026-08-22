import os
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path

ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
release_name = f'GGG_Production_Release_v0.1.0_{ts}'
zip_filename = f'{release_name}.zip'

include_extensions = {'.py', '.html', '.css', '.js', '.bat', '.ps1', '.db', '.md'}
exclude_dirs = {'__pycache__', '.git', '.vscode', 'audit_snapshots'}

print(f'>>> Creating release package: {zip_filename}')

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in include_extensions and not file.endswith('.zip'):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)

# Compute SHA-256 checksum of the entire release bundle
hasher = hashlib.sha256()
with open(zip_filename, 'rb') as f:
    while chunk := f.read(8192):
        hasher.update(chunk)
bundle_hash = hasher.hexdigest()

manifest_file = f'{release_name}_MANIFEST.txt'
with open(manifest_file, 'w') as f:
    f.write(f'GARZA GLOBAL GRAVITON - RELEASE v0.1.0\n')
    f.write(f'Timestamp UTC: {datetime.utcnow().isoformat()}\n')
    f.write(f'Bundle Archive: {zip_filename}\n')
    f.write(f'SHA-256 Checksum: {bundle_hash}\n')

print(f'SUCCESS: Release package and manifest created.')
print(f'Archive Checksum: {bundle_hash}')
