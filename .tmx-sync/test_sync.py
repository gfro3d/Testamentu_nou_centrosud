import io
import json
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_gospels as sync

class VerseTests(unittest.TestCase):
    def test_number_inside_fully_numbered_verse_is_not_a_marker(self):
        value = "2,1 Primo versetto.\n2,2 Secondo versetto.\n2,3 Frase con 16 parole.\n2,4 Quarto versetto."
        records = sync.markers(value)
        self.assertEqual([r["verse"] for r in records], [1,2,3,4])
        self.assertIn("16 parole", records[2]["text"])

    def test_editorial_braces_and_dashes_start_a_verse(self):
        records = sync.markers("1,7 Primo.\n1,8 {E fit} Parole.\n1,9 - Seconda parte.")
        self.assertEqual([r["verse"] for r in records], [7,8,9])

    def test_bare_final_verse_in_numbered_document(self):
        records = sync.markers("21,41 Primo.\n21,42 Secondo.\n21,43 Terzo.\n21,44 Quarto.\n45 Ultimo.")
        self.assertEqual([r["verse"] for r in records], [41,42,43,44,45])

    def test_reference_footnotes_are_not_duplicate_verses(self):
        records = sync.markers("16,9 Primo.\n16,10 Secondo.\n16,11 Terzo.\n16,12 Quarto.\n16,9 Mc 10,11-12 1")
        self.assertEqual([r["verse"] for r in records], [9,10,11,12])

    def test_placeholder_in_italian_is_excluded(self):
        rows, excluded = sync.align("Mt", 23, {13:"Prima frase",14:"[]",15:"Terza frase"},
            [{"verse":13,"text":"Primu"},{"verse":14,"text":"Testu sardu"},{"verse":15,"text":"Tertzu"}], "centro_sud")
        self.assertEqual([r[0] for r in rows], ["Mt23,13","Mt23,15"])
        self.assertEqual(excluded, ["Mt23,14"])

    def test_full_verse_not_sentences(self):
        raw = sync.make_tmx([("Mt1,1", "Prima frase.\nSeconda frase & terza.", "Primu.\nSegundu <testu>.")], "centro_nord")
        root = ET.fromstring(raw)
        self.assertEqual(len(root.findall("body/tu")), 1)
        self.assertEqual([s.text for s in root.findall("body/tu/tuv/seg")],
            ["Mt1,1 Prima frase. Seconda frase & terza.", "Mt1,1 Primu. Segundu <testu>."])

    def test_duplicate_reference_rejected(self):
        with self.assertRaises(sync.SyncError):
            sync.make_tmx([("Lc1,1", "Testo", "Testu"), ("Lc1,1", "Altro", "Àteru")], "centro_sud")

    def test_range_reference_rejected(self):
        with self.assertRaises(sync.SyncError):
            sync.make_tmx([("Mt21,45–46", "Testo", "Testu")], "centro_nord")

    def test_inline_and_nonbreaking_numbers(self):
        records = sync.markers("1.1.Cumintzu de s'evangèliu de Gesùs Cristos, Fizu de Deus. 2\u00a0Comente est iscritu.3 E fint andados.")
        self.assertEqual([r["verse"] for r in records], [1,2,3])
        self.assertTrue(records[2]["text"].startswith("E fint"))

    def test_table_docx_extraction(self):
        document = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>8,1 Text in a table</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("word/document.xml", document)
        self.assertIn("Text in a table", sync.extract(stream.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))

    def test_variant_order_is_not_assumed(self):
        north = [{"text": "sos sas fizu fizos dischentes narende fit sos sas"}]
        south = [{"text": "is fillu fillus discìpulus narendi fiat is fillu"}]
        self.assertEqual(sync.variant_of(north), "centro_nord")
        self.assertEqual(sync.variant_of(south), "centro_sud")

    def test_uncertain_variant_rejected(self):
        with self.assertRaises(sync.SyncError):
            sync.variant_of([{"text": "Gesùs"}])

    def test_verified_merged_boundary(self):
        source = {45: "Udite queste parabole capirono e cercavano di catturarlo; ma avevano paura."}
        target = {45: "Intendende custas paràulas e fint chirchende de lu tènnere; ma fint timende."}
        sync.repair_known("Mt", 21, source, target, "centro_nord")
        self.assertEqual(sorted(target), [45,46])
        self.assertEqual(source[46], "e cercavano di catturarlo; ma avevano paura.")

    def test_editorial_case_not_arbitrarily_split(self):
        source = {21: "Dal cuore...", 22: "Altre cose..."}
        target = {21: "Lista riordinata che non può essere divisa"}
        sync.repair_known("Mc",7,source,target,"centro_sud")
        self.assertNotIn(21,target)

    def test_unknown_gap_rejected(self):
        with self.assertRaises(sync.SyncError):
            sync.align("Lc",1,{1:"Uno",2:"Due",3:"Tre"},
                [{"verse":1,"text":"Unu"},{"verse":3,"text":"Tres"}],"centro_nord")

    def test_partial_chapter_allowed_but_reported(self):
        rows, excluded = sync.align("Lc",18,{1:"Primo versetto",2:"Secondo versetto"},
            [{"verse":1,"text":"Primu versettu"}],"centro_nord")
        self.assertEqual(len(rows),1)
        self.assertEqual(excluded,["Lc18,2"])

    def test_public_output_has_no_source_metadata(self):
        data=sync.make_tmx([("Mc1,1","Inizio","Cumintzu")],"centro_sud").decode()
        self.assertNotIn("drive.google",data)
        self.assertNotIn("source_url",data)

if __name__ == "__main__":
    unittest.main()
