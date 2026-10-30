"""Record current package metadata only; never train, infer, install or load weights."""
import importlib.metadata,json,platform,sys
from datetime import datetime,timezone
packages={}
for name in ['ultralytics','torch','torchvision','paddleocr','paddlepaddle','paddlepaddle-gpu','paddlex','opencv-python','opencv-python-headless','Pillow','numpy','pandas']:
 try:packages[name]=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:packages[name]=None
print(json.dumps({'recorded_at':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'packages':packages,'scope':'Current environment only, not proof of the historical training/OCR environment'},indent=2))
