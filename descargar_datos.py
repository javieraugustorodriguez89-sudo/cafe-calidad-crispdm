"""Descarga local de la fuente pública. El CSV original no se republica."""
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
from io import BytesIO

def descargar():
    root=Path(__file__).resolve().parent/'data';root.mkdir(exist_ok=True)
    url='https://www.kaggle.com/api/v1/datasets/download/volpatto/coffee-quality-database-from-cqi'
    with urlopen(url,timeout=60) as response:content=response.read()
    with ZipFile(BytesIO(content)) as z:
        (root/'arabica_data_cleaned.csv').write_bytes(z.read('arabica_data_cleaned.csv'))
    return root/'arabica_data_cleaned.csv'

if __name__=='__main__':print(descargar())
