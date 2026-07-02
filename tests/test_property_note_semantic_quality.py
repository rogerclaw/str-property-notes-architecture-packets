from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.lib import property_note_semantic_quality as semantic


GOOD_BODY = """
<h1>Sample Property Dossier</h1>
<h2>Access &amp; Codes</h2><ul><li><b>Front door keypad:</b> Door/keypad code: [REDACTED_ACCESS_CODE].</li></ul>
<h2>Contacts</h2><ul><li><b>Owner - One:</b> Email: [REDACTED_EMAIL_1].</li><li><b>Owner - Two:</b> Email: [REDACTED_EMAIL_2].</li><li><b>Cleaner:</b> phone [REDACTED_PHONE].</li></ul>
<h2>Wi-Fi / Systems</h2><ul><li><b>Wi-Fi network:</b> Network: ISP 2832.</li><li><b>Wi-Fi password:</b> Password: private.</li></ul>
<h2>Field Basics</h2><ul><li><b>Address:</b> 123 Example St, Sample City, ST 00000.</li><li><b>Trash pickup:</b> Tuesday collection.</li><li><b>Trash can location:</b> right side facing the house.</li></ul>
<h2>Links</h2><ul><li><b>Airbnb listing:</b> https://www.airbnb.com/rooms/123</li><li><b>House manual:</b> https://www.canva.com/design/abc/view</li></ul>
<br><h2>Evidence / Refresh Notes</h2>
<h3>Occupancy &amp; Money</h3><ul><li><b>Year to date:</b> 10 accepted bookings / 40 nights.</li><li><b>Trailing year:</b> 20 accepted bookings / 80 nights.</li></ul>
<h3>Current / Upcoming Stays</h3><ul><li><b>Current:</b> Guest A is in house.</li><li><b>Next 1:</b> Guest B tomorrow.</li></ul>
<h3>Owner Communication Snapshot</h3><ul><li><b>Owner snapshot:</b> owners on file.</li><li><b>Owner operating note:</b> permit context.</li></ul>
<h3>Cleaner Message Activity</h3><ul><li><b>Cleaner snapshot:</b> cleaner on file.</li><li><b>Cleaner activity:</b> coordinate by property name.</li></ul>
<h3>Other Message Activity</h3><ul><li><b>Guest messaging:</b> threads on reservations.</li><li><b>Vendor/context messages:</b> design context.</li></ul>
<h3>Charles Visit Stats</h3><ul><li><b>Confirmed visits:</b> field history exists.</li><li><b>Field use:</b> onsite scan.</li></ul>
<h3>Difficulty Ranking</h3><ul><li><b>Management difficulty:</b> Medium.</li><li><b>Risk driver:</b> access role confusion.</li></ul>
<h3>Airbnb / Review Signal</h3><ul><li><b>rating:</b> 4.9/5.</li><li><b>Listing context:</b> listing id on file.</li></ul>
<h3>Recent Notable Events</h3><ul><li><b>Recent event:</b> note repaired.</li><li><b>Recent source event:</b> reservation refreshed.</li></ul>
<h3>Repairs / Maintenance To Do</h3><ul><li><b>Repair:</b> lock invoice on file.</li><li><b>Maintenance watch:</b> access hardware.</li></ul>
<h3>Management Notes</h3><ul><li><b>Management guidance:</b> use locked note.</li><li><b>Manager use:</b> add verified contacts only.</li></ul>
<h3>Source / Refresh Notes</h3><ul><li><b>Refresh:</b> Refreshed July 2 from source families.</li><li><b>Permit/design note:</b> EHS on file.</li></ul>
"""


class PropertyNoteSemanticQualityTests(unittest.TestCase):
    def test_good_manager_body_passes(self) -> None:
        self.assertTrue(semantic.evaluate_body(GOOD_BODY)["ok"])

    def test_forbids_false_no_publish_text(self) -> None:
        result = semantic.evaluate_body(GOOD_BODY + "<p>No Apple Notes publish occurred.</p>")
        self.assertFalse(result["ok"])

    def test_forbids_visible_html_link_markup(self) -> None:
        result = semantic.evaluate_body(GOOD_BODY + '<p><a href="https://example.com">bad</a></p>')
        self.assertFalse(result["ok"])

    def test_forbids_progress_paths(self) -> None:
        result = semantic.evaluate_body(GOOD_BODY + "<p>ops/progress/bad.json</p>")
        self.assertFalse(result["ok"])

    def test_forbids_negative_unknown_rows(self) -> None:
        result = semantic.evaluate_body(GOOD_BODY + "<p>No verified sample-property-specific neighbor contact found.</p>")
        self.assertFalse(result["ok"])

    def test_requires_source_receipt_families(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = Path(tempdir) / "receipt.json"
            receipt.write_text(json.dumps({"source_families": []}))
            result = semantic.evaluate_source_receipts("sample_property", receipt)
            self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
