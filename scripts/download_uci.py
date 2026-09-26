"""Download and extract the official UCI Online Retail II workbook."""
from pathlib import Path
import hashlib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
EXPECTED_WORKBOOK_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"


def main():
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "online_retail_ii.zip"
    workbook = raw / "online_retail_II.xlsx"
    if not workbook.is_file():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, archive)
        with zipfile.ZipFile(archive) as bundle:
            member = next((name for name in bundle.namelist() if name.lower().endswith(".xlsx")), None)
            if not member:
                raise ValueError("The UCI archive does not contain an .xlsx workbook.")
            with bundle.open(member) as source, workbook.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    if digest != EXPECTED_WORKBOOK_SHA256:
        raise ValueError(f"Unexpected workbook SHA-256: {digest}")
    print(f"Verified {workbook} ({digest})")


if __name__ == "__main__":
    main()
