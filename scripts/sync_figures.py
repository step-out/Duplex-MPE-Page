#!/usr/bin/env python3
"""Copy manuscript figures and regenerate matching web previews.

Usage: python scripts/sync_figures.py --paper-dir ../paper_iclr
Requires PyMuPDF and Pillow.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil

import fitz
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    html_path = root / 'index.html'
    html = html_path.read_text()
    provenance_path = root / 'assets/provenance.json'
    provenance = json.loads(provenance_path.read_text())
    previews = provenance.setdefault('figurePreviews', {})
    for name in ('framework', 'dataset_pipeline', 'response_metrics'):
        source = args.paper_dir / 'figures' / f'{name}.pdf'
        target = root / 'assets/figures' / source.name
        shutil.copyfile(source, target)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        with fitz.open(source) as doc:
            page = doc[0]
            scale = 2200 / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        preview = target.with_suffix('.webp')
        Image.open(io.BytesIO(pix.tobytes('png'))).save(preview, quality=94, method=6)
        preview_hash = hashlib.sha256(preview.read_bytes()).hexdigest()
        for suffix, digest in [('pdf', source_hash), ('webp', preview_hash)]:
            asset = f'assets/figures/{name}.{suffix}'
            html, replaced = re.subn(
                rf'((?:src|href)="){re.escape(asset)}(?:\?[^\"]*)?"',
                rf'\g<1>{asset}?v={digest[:12]}"', html)
            if not replaced:
                raise ValueError(f'No HTML reference found for {asset}')
        pattern = rf'(<img src="assets/figures/{name}\.webp[^\"]*" width=")\d+(" height=")\d+'
        html, replaced = re.subn(pattern, rf'\g<1>{pix.width}\g<2>{pix.height}', html)
        if replaced != 1:
            raise ValueError(f'Expected one image with dimensions for {name}')
        provenance['paperSources'][f'figures/{name}.pdf'] = source_hash
        previews[name] = {'pdfSha256': source_hash, 'webpSha256': preview_hash,
                          'width': pix.width, 'height': pix.height, 'pdfPage': 1}
        print(f'{name}: {pix.width} x {pix.height}; PDF {source_hash[:12]}')
    html_path.write_text(html)
    provenance_path.write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    main()
