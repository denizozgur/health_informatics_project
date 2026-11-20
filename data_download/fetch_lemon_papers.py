"""Retain primary articles and supplements locally for the LEMON review."""

import io
import json
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from fetch_lemon import SOURCE, save


def main():
    records = []
    for name, pmc in [("babayan2019", "PMC6371893"), ("lin2026", "PMC13487156")]:
        base = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}"
        article = SOURCE / f"{name}.xml"
        records.append(save(base + "/fullTextXML", article))
        root = ET.parse(article).getroot()
        (SOURCE / f"{name}.txt").write_text("\n\n".join(
            "".join(sec.itertext()) for sec in root.findall("./body/sec")))
        archive = SOURCE / f"{name}_supplements.zip"
        records.append(save(base + "/supplementaryFiles", archive))
        with ZipFile(archive) as supplements:
            for member in supplements.namelist():
                if not member.endswith((".docx", ".zip")):
                    continue
                payload = supplements.read(member)
                filename = member.rsplit("/", 1)[-1]
                (SOURCE / filename).write_bytes(payload)
                if filename.endswith(".docx"):
                    with ZipFile(io.BytesIO(payload)) as document:
                        tree = ET.fromstring(document.read("word/document.xml"))
                        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                        text = "\n".join("".join(t.text or "" for t in p.findall(".//w:t", ns))
                                         for p in tree.findall(".//w:p", ns))
                        (SOURCE / filename).with_suffix(".txt").write_text(text)
    (SOURCE / "papers_manifest.json").write_text(json.dumps(records, indent=2))
    print("Retained two full-text articles and their supplementary archives")


if __name__ == "__main__":
    main()
