"""Drive -> verse-aligned OmegaT TMX. Private configuration is supplied only by secrets."""
import copy
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

LANG = "{http://www.w3.org/XML/1998/namespace}lang"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PREFIXES = {"Matteo": "Mt", "Marco": "Mc", "Luca": "Lc", "Giovanni": "Gv"}
MARKER = re.compile(r"""(?<![\w,])(?:(\d{1,2})\s*[,.]\s*(\d{1,2})[.;]?\s*|(\d{1,2})[.;]?\s+)(?=[^\W\d_]|[«“"'¿(\[{}–—-])""")
KNOWN_OMISSIONS = {"Mc7,16", "Mc9,44", "Mc9,46", "Mc11,26", "Mc15,28"}

class SyncError(Exception):
    pass

def normal(text):
    return re.sub(r"\s+", " ", text).strip()

def meaningful(text):
    return bool(re.search(r"[^\W\d_]", text))

def markers(text):
    # Remove explicit marginal cross-references before detecting numeric boundaries.
    text = re.sub(r"\(?\b(?:Mt|Mc|Lc|Gv|Matteo)\.?\s+\d+[,.:]\d+(?:[-–]\d+)?\)?", "", text)
    matches = list(MARKER.finditer(text.lstrip("\ufeff")))
    text = text.lstrip("\ufeff")
    full = [m for m in matches if m[1]]
    bare = [m for m in matches if not m[1]]
    # Fully numbered documents must not interpret ordinary inline numbers as verses.
    # Compact documents (one chapter reference followed by bare verse numbers) still work.
    if sum(int(m[2]) > 1 for m in full) >= 3 and len(full) >= 3 * len(bare):
        matches = [m for m in matches if m[1] or not text[:m.start()].rsplit("\n", 1)[-1].strip()]
    records = []
    chapter = None
    for i, match in enumerate(matches):
        if match[1]:
            chapter = int(match[1])
        if chapter is None:
            continue
        verse = int(match[2] or match[3])
        value = text[match.end():matches[i+1].start() if i+1 < len(matches) else len(text)]
        value = re.sub(r"\s*(?:\[\d+\]|\(\d+\))\s*$", "", value).strip()
        if re.fullmatch(r"(?:Mt|Mc|Lc|Gv)\.?\s*\d+[\d,;:\s–—-]*", normal(value)):
            # A marginal reference is not a second translation of this verse.
            continue
        records.append({"chapter": chapter, "verse": verse, "text": value})
    return records

def split_blocks(records):
    starts = [i for i, r in enumerate(records) if r["verse"] == 1 and
              len(normal(r["text"])) >= 40 and meaningful(r["text"])]
    return [records[a:b] for a, b in zip(starts, starts[1:] + [len(records)])]

def unique_map(records):
    result = {}
    for record in records:
        v = record["verse"]
        if v in result:
            raise SyncError(f"Capitolo {record.get('chapter', '?')}, versetto {v}: numerazione duplicata.")
        result[v] = record["text"]
    return result

def variant_of(records):
    text = " ".join(r["text"] for r in records).lower()
    north = len(re.findall(r"\b(?:sos|sas|fizu|fizos|dischentes|narende|fit)\b", text))
    south = len(re.findall(r"\b(?:is|fillu|fillus|discìpulus|narendi|fiat)\b", text))
    if max(north, south) < 3 or abs(north-south) < 3:
        raise SyncError("Variante linguistica non identificabile con sicurezza.")
    return "centro_nord" if north > south else "centro_sud"

def split_at(mapping, verse, boundary):
    if verse + 1 in mapping:
        return
    value = mapping.get(verse, "")
    if value.count(boundary) != 1:
        raise SyncError("Confine di due versetti non verificabile.")
    a, b = value.split(boundary, 1)
    mapping[verse] = a.strip()
    mapping[verse+1] = (boundary + b).strip()

def repair_known(prefix, chapter, source, target, variant):
    # Only verified boundaries; no lexical rewriting.
    if prefix == "Mt" and chapter == 21:
        split_at(source, 45, " e cercavano di catturarlo;")
        boundary = " e fint chirchende de lu tènnere;" if variant == "centro_nord" else " e fiant circhendi de dd'aciapai;"
        split_at(target, 45, boundary)
    if prefix == "Mc" and chapter == 13 and variant == "centro_sud":
        split_at(target, 2, " Luegus sendi sètziu")
    if prefix == "Mc" and chapter == 7 and variant == "centro_sud" and 22 not in target:
        # The source interleaves both verses: exclude both until editorially resolved.
        target.pop(21, None)

def align(prefix, chapter, italian, records, variant):
    source, target = copy.deepcopy(italian), unique_map(records)
    repair_known(prefix, chapter, source, target, variant)
    result, excluded = [], []
    for verse in sorted(set(source) | set(target)):
        ref = f"{prefix}{chapter},{verse}"
        a, b = source.get(verse, ""), target.get(verse, "")
        if ref == "Mt2,4" and variant == "centro_nord" and re.search(r"the dead man sat up", b, re.I):
            # Verified foreign-text contamination inside this source verse; do not rewrite it.
            excluded.append(ref)
            continue
        if not meaningful(a) or not meaningful(b):
            approved = ref in KNOWN_OMISSIONS or (prefix == "Mc" and variant == "centro_sud" and ref in {"Mc1,40", "Mc7,21", "Mc7,22"})
            trailing_partial = verse > max(target, default=0)
            placeholder = ((verse in target and not meaningful(target[verse])) or
                           (verse in source and not meaningful(source[verse])))
            if not (approved or trailing_partial or placeholder):
                side = "italiano" if not meaningful(a) else "sardo"
                raise SyncError(f"{ref}: coppia incompleta ({side}), revisione necessaria.")
            excluded.append(ref)
            continue
        a, b = normal(a), normal(b)
        # No remaining numbered verse markers inside a single verse.
        if re.search(r"(?<!\w)\d{1,2}[,.]\d{1,2}\s", b):
            # Preserve explicit marginal cross references as notes, not new segments.
            b = re.sub(r"\(?\b(?:Mt\.?|Mc\.?|Lc\.?|Gv\.?|Matteo)\s+\d+,\d+(?:[-–]\d+)?\)?", "", b)
        b = normal(b)
        result.append((ref, a, b))
    return result, excluded

def make_tmx(rows, variant):
    root = ET.Element("tmx", version="1.4")
    header = ET.SubElement(root, "header", {"creationtool": "gospel-tmx-sync",
        "creationtoolversion": "1.0", "segtype": "paragraph", "o-tmf": "PlainText",
        "adminlang": "it-IT", "srclang": "it-IT", "datatype": "PlainText"})
    ET.SubElement(header, "prop", type="x-target-variant").text = variant
    body = ET.SubElement(root, "body")
    seen = set()
    for ref, italian, sardinian in rows:
        if ref in seen or not re.fullmatch(r"(?:Mt|Mc|Lc|Gv)\d+,\d+", ref):
            raise SyncError("Identificativo TMX non valido o duplicato.")
        seen.add(ref)
        tu = ET.SubElement(body, "tu", tuid=ref.replace(",", "_"))
        ET.SubElement(tu, "prop", type="x-reference").text = ref
        for lang, value in (("it-IT", italian), ("sc", sardinian)):
            if not meaningful(value):
                raise SyncError("Segmento vuoto.")
            ET.SubElement(ET.SubElement(tu, "tuv", {LANG: lang}), "seg").text = ref + " " + normal(value)
    ET.indent(root, space="  ")
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    check = ET.fromstring(data).findall("body/tu")
    if len(check) != len(rows):
        raise SyncError("Conteggio TMX non valido.")
    for tu, expected in zip(check, rows):
        variants = tu.findall("tuv")
        if [v.get(LANG) for v in variants] != ["it-IT", "sc"]:
            raise SyncError("Lingue TMX non valide.")
        actual = [v.find("seg").text for v in variants]
        wanted = [expected[0] + " " + normal(v) for v in expected[1:]]
        if actual != wanted or any("\n" in v or "\r" in v for v in actual):
            raise SyncError("Testo TMX non preservato.")
    return data + b"\n"

def extract(raw, mime):
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            return "\n".join("".join((t.text or "") if t.tag == W+"t" else "\n" if t.tag in {W+"br", W+"cr"} else "\t" if t.tag == W+"tab" else "" for t in p.iter()) for p in root.iter(W+"p"))
    if raw.lstrip().startswith(b"{\\rtf"):
        from striprtf.striprtf import rtf_to_text
        return rtf_to_text(raw.decode("latin-1"))
    if mime == "text/plain":
        return raw.decode("utf-8-sig")
    raise SyncError("Formato sorgente non supportato: nessun output sostituito.")

class Drive:
    def __init__(self, credentials):
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        auth = service_account.Credentials.from_service_account_info(
            credentials, scopes=["https://www.googleapis.com/auth/drive.readonly"])
        self.http = AuthorizedSession(auth)

    def get(self, path, params=None, binary=False):
        response = self.http.get("https://www.googleapis.com/drive/v3/" + path,
                                 params=params, timeout=90)
        if response.status_code != 200:
            raise SyncError(f"Accesso Drive non riuscito (HTTP {response.status_code}).")
        return response.content if binary else response.json()

    def children(self, folder):
        files, token = [], None
        while True:
            params = {"q": f"'{folder}' in parents and trashed = false", "pageSize": 1000,
                      "fields": "files(id,name,mimeType),nextPageToken",
                      "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            if token:
                params["pageToken"] = token
            page = self.get("files", params)
            files.extend(page.get("files", []))
            token = page.get("nextPageToken")
            if not token:
                return files

    def read(self, item):
        fid, mime = item["id"], item["mimeType"]
        if mime == "application/vnd.google-apps.document":
            return self.get(f"files/{fid}/export", {"mimeType": "text/plain"}, True).decode("utf-8-sig")
        return extract(self.get(f"files/{fid}", {"alt": "media", "supportsAllDrives": "true"}, True), mime)

    def document(self, fid):
        return self.get(f"files/{fid}", {"fields": "id,mimeType", "supportsAllDrives": "true"})

def omega_output():
    project = ET.parse("omegat.project")
    directory = project.findtext("./project/tm_dir")
    if directory not in (None, "__DEFAULT__", "tm"):
        raise SyncError("tm_dir personalizzato: configurazione manuale necessaria.")
    return Path("tm/controllo-teologia")

def run(config, credentials, variant):
    drive = Drive(credentials)
    output = omega_output()
    state_path = Path(".tmx-sync/state.json")
    old = json.loads(state_path.read_text()) if state_path.exists() else {}
    state = {"schema_version": 2, "variant": variant, "branch": "main",
             "initial_sync_completed": True, "managed_output_directory": str(output), "outputs": {}}
    planned, problems = {}, []
    configured_names = set()
    for book in config["books"]:
        name, prefix = book["name"], book["prefix"]
        if PREFIXES.get(name) != prefix or name in configured_names:
            raise SyncError("Configurazione dei Vangeli non valida.")
        configured_names.add(name)
        parent_files = drive.children(book["folder_id"])
        folders = [f for f in parent_files if f["mimeType"] == "application/vnd.google-apps.folder"
                   and re.search(r"controll", f["name"], re.I)]
        control_id = book.get("control_folder_id")
        if not control_id:
            if len(folders) > 1:
                raise SyncError("Più cartelle di controllo candidate.")
            control_id = folders[0]["id"] if folders else None
        if not control_id:
            if any(name + "_" in key for key in old.get("outputs", {})):
                raise SyncError("Cartella di controllo non più disponibile.")
            continue
        files = drive.children(control_id)
        chapter_files = {}
        for f in files:
            match = re.search(r"\bcap\.\s*(\d+)", f["name"], re.I)
            if not match:
                continue
            chapter = int(match[1])
            if chapter in chapter_files:
                raise SyncError("Più fonti per lo stesso capitolo.")
            chapter_files[chapter] = f
        if not chapter_files:
            raise SyncError("Cartella di controllo senza capitoli leggibili.")
        italian_text = drive.read(drive.document(book["italian_file_id"]))
        italian_blocks = split_blocks(markers(italian_text))
        italian = {}
        for block in italian_blocks:
            chapter = block[0]["chapter"]
            if chapter in italian:
                raise SyncError("Capitoli italiani duplicati.")
            italian[chapter] = unique_map(block)
        rows, excluded = [], []
        for chapter, item in sorted(chapter_files.items()):
            if chapter not in italian:
                raise SyncError("Capitolo senza corrispondente italiano.")
            blocks = split_blocks(markers(drive.read(item)))
            if not 1 <= len(blocks) <= 2:
                raise SyncError("Blocchi di traduzione non riconosciuti.")
            by_variant = {}
            for block in blocks:
                label = variant_of(block)
                if label in by_variant:
                    raise SyncError("Due blocchi con la stessa variante.")
                by_variant[label] = block
            if variant not in by_variant:
                continue
            matched, missing = align(prefix, chapter, italian[chapter], by_variant[variant], variant)
            if not matched or matched[0][0] != f"{prefix}{chapter},1":
                raise SyncError("Inizio del capitolo non allineato.")
            rows.extend(matched)
            # Keep coverage exceptions as references, never Drive metadata.
            excluded.extend(missing)
        if not rows:
            raise SyncError("Nessun versetto per la variante richiesta.")
        filename = f"{name}_it_sc_{variant}.tmx"
        path = output / filename
        data = make_tmx(rows, variant)
        if path.exists():
            previous = ET.fromstring(path.read_bytes()).findall("body/tu")
            prior_refs = {u.findtext("prop[@type='x-reference']") for u in previous}
            if not prior_refs <= {r[0] for r in rows}:
                raise SyncError("Perdita di versetti rispetto alla TMX pubblicata.")
        planned[path] = data
        state["outputs"][filename] = {"sha256": hashlib.sha256(data).hexdigest(),
            "units": len(rows), "first": rows[0][0], "last": rows[-1][0],
            "excluded_references": sorted(set(excluded))}
        if excluded:
            problems.append(f"{name}: {len(set(excluded))} riferimenti senza coppia completa.")
    if not planned:
        raise SyncError("Nessuna TMX generabile.")
    for previous in old.get("outputs", {}):
        if previous not in state["outputs"]:
            raise SyncError("Perdita di una memoria già pubblicata.")
    for path, data in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## TMX validate\n")
            for filename, info in state["outputs"].items():
                handle.write(f"- {filename}: {info['units']} versetti ({info['first']} – {info['last']}).\n")
            for problem in problems:
                handle.write("- " + problem + "\n")

def main():
    try:
        config = json.loads(os.environ["GOOGLE_DRIVE_SYNC_CONFIG"])
        credentials = json.loads(os.environ["GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON"])
        variant = os.environ["TMX_VARIANT"]
        if variant not in ("centro_nord", "centro_sud"):
            raise SyncError("Variante non valida.")
        run(config, credentials, variant)
    except SyncError as error:
        print("::error::" + str(error))
        return 1
    except Exception:
        # Never dump request URLs, source text, file IDs, or credential exceptions.
        print("::error::Sincronizzazione interrotta. Verificare configurazione privata, accessi e formati delle fonti.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
