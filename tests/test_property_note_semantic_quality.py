from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import fresh_replace_property_information_note as fresh_replace
import property_note_semantic_quality as semantic
import str_property_fact_registry as registry


GOOD_BODY = registry.build_private_operations_note("sample_property")
FIVE_EIGHTEEN_SHAPED_BODY = """<h1>123 Example St, Sample City, ST 00000 - Deluxe Dossier</h1>
<h2>Access &amp; Codes</h2>
<ul>
<li><b>Front door guest code:</b> Door/keypad code uses SAMPLE_GUEST_ACCESS_VALUE.</li>
<li><b>Lock admin/programming code:</b> Admin/programming code uses SAMPLE_ADMIN_ACCESS_VALUE.</li>
</ul>
<h2>Contacts</h2>
<ul>
<li><b>Owner - Owner A:</b> SAMPLE_OWNER_CONTACT.</li>
<li><b>Cleaner / turnover - Cleaner A:</b> SAMPLE_CLEANER_CONTACT.</li>
</ul>
<h2>Wi-Fi / Systems</h2>
<ul>
<li><b>Wi-Fi network:</b> Network: SAMPLE-NETWORK.</li>
<li><b>Wi-Fi password:</b> Password uses SAMPLE_WIFI_SECRET.</li>
</ul>
<h2>Field Basics</h2>
<ul>
<li><b>Address:</b> 123 Example St, Sample City.</li>
<li><b>Parking:</b> Driveway/curb plan is in the field note.</li>
<li><b>Trash:</b> Trash cans are on the right side facing the house; normal pickup Tuesday.</li>
</ul>
<h2>Links</h2>
<ul>
<li><b>Airbnb listing:</b> Airbnb listing link is saved for manager review.</li>
<li><b>House manual:</b> House manual, permit, and map links are grouped here for field use.</li>
</ul>
<h2>Evidence / Refresh Notes</h2>
<h3>Occupancy &amp; Money</h3>
<ul>
<li><b>YTD bookings:</b> Bookings, nights, revenue trend, and occupancy context are summarized here.</li>
</ul>
<h3>Current / Upcoming Stays</h3>
<ul>
<li><b>Current:</b> No current in-house accepted stay in the sample packet.</li>
<li><b>Next 1:</b> Next accepted stay is held in the reservation system; refresh before guest-specific action.</li>
</ul>
<h3>Owner &amp; Message Activity</h3>
<ul>
<li><b>Owner thread:</b> Owner, cleaner, and guest message activity is grouped by role before action.</li>
</ul>
<h3>Charles Visit Stats</h3>
<ul>
<li><b>Charles visits:</b> Visit count and last-seen status summarize field recency for this property.</li>
</ul>
<h3>Difficulty Ranking</h3>
<ul>
<li><b>Difficulty:</b> Medium manager difficulty based on access, turnover, and owner-contact complexity.</li>
</ul>
<h3>Airbnb / Review Signal</h3>
<ul>
<li><b>Airbnb reviews:</b> Review/rating signal is summarized here for manager awareness.</li>
</ul>
<h3>Recent Notable Events</h3>
<ul>
<li><b>Recent event:</b> Latest maintenance, guest, or owner item is summarized in manager language.</li>
</ul>
<h3>Active Ops Watchlist</h3>
<ul>
<li><b>Watchlist:</b> Confirm access and turnover readiness when the next same-day arrival appears.</li>
</ul>
<h3>Management Notes</h3>
<ul>
<li><b>Manager note:</b> Keep owner escalation, cleaner dispatch, and guest access facts separated by role.</li>
</ul>
<h3>Source / Refresh Notes</h3>
<ul>
<li><b>Refresh:</b> Refreshed from current note, locked property records, owner/message sources, reservations, house manual/docs, and maintenance artifacts.</li>
</ul>
"""
GOOD_CLOSEOUT = """# Public closeout

- Private operations note semantic gate: PASS
- Public redaction gate: PASS
- Raw codes, passwords, phones, emails, and source bodies are withheld.
"""


class PrivateOperationsSemanticGateTests(unittest.TestCase):
    def test_good_private_operations_note_passes(self) -> None:
        self.assertTrue(semantic.evaluate_body(GOOD_BODY)["ok"])

    def test_sanitized_518_deluxe_dossier_fixture_passes(self) -> None:
        result = semantic.evaluate_body(FIVE_EIGHTEEN_SHAPED_BODY)
        self.assertTrue(result["ok"], result["findings"])
        self.assertIn("Evidence / Refresh Notes", result["section_row_counts"])
        self.assertIn("Source / Refresh Notes", result["section_row_counts"])

    def test_rejects_audit_report_shape(self) -> None:
        body = GOOD_BODY.replace("<h2>Evidence / Refresh Notes</h2>", "<h2>Gate Summary</h2>", 1)
        result = semantic.evaluate_body(body)
        self.assertFalse(result["ok"])
        self.assertIn("private_audit_shape", {row["check"] for row in result["findings"]})

    def test_rejects_source_path_and_process_rows(self) -> None:
        body = GOOD_BODY + "<p>Gate result: PASS from ops/progress/sample.json in a dry-run review packet.</p>"
        result = semantic.evaluate_body(body)
        self.assertFalse(result["ok"])
        self.assertIn("forbidden_process_text", {row["check"] for row in result["findings"]})

    def test_rejects_generic_filler(self) -> None:
        body = GOOD_BODY.replace("Latest maintenance, guest, or owner item is summarized in manager language.", "Owner is responsive and routine maintenance normal.")
        result = semantic.evaluate_body(body)
        self.assertFalse(result["ok"])
        self.assertIn("generic_filler", {row["check"] for row in result["findings"]})

    def test_missing_and_candidate_text_only_allowed_in_needs_confirmation(self) -> None:
        bad = GOOD_BODY.replace("Driveway/curb plan is in the field note.", "CANDIDATE driveway plan not found.")
        self.assertFalse(semantic.evaluate_body(bad)["ok"])
        candidate_slots = registry.sample_fact_slots()
        candidate_slots.append(
            {
                "slot_id": "contact.local_helper.candidate",
                "section": "Management Notes",
                "target_section": "Management Notes",
                "label": "CANDIDATE - local helper",
                "state": "candidate_unconfirmed",
                "public_summary": "CANDIDATE appears in owner-message context, not promoted.",
                "role": "local_helper",
            }
        )
        body = registry.build_private_operations_note("sample_property", candidate_slots)
        self.assertTrue(semantic.evaluate_body(body)["ok"])

    def test_private_mode_rejects_redaction_placeholders_for_required_private_fields(self) -> None:
        body = GOOD_BODY.replace("Door/keypad code uses SAMPLE_GUEST_ACCESS_VALUE.", "Door/keypad code: [REDACTED_ACCESS_CODE].")
        result = semantic.evaluate_body(body)
        self.assertFalse(result["ok"])
        self.assertIn("access_contract", {row["check"] for row in result["findings"]})


class FactSlotResolutionTests(unittest.TestCase):
    def test_candidate_contact_must_be_labeled(self) -> None:
        slots = registry.sample_fact_slots()
        slots.append(
            {
                "slot_id": "contact.vendor.possible",
                "section": "Management Notes",
                "target_section": "Management Notes",
                "label": "possible vendor",
                "state": "candidate_unconfirmed",
                "role": "vendor",
            }
        )
        result = registry.evaluate_fact_slot_resolution(slots)
        self.assertFalse(result["ok"])
        self.assertIn("candidate_contact_label", {row["check"] for row in result["findings"]})

    def test_owner_email_conflict_blocks_until_conflict_state(self) -> None:
        slots = registry.sample_fact_slots() + [
            {
                "slot_id": "contact.owner.email_a",
                "section": "Contacts",
                "label": "Owner email A",
                "state": "resolved_verified",
                "role": "owner",
                "subtype": "email",
                "value_hash": "owner_email_a",
                "value_for_private_note": "SAMPLE_OWNER_A_EMAIL",
            },
            {
                "slot_id": "contact.owner.email_b",
                "section": "Contacts",
                "label": "Owner email B",
                "state": "resolved_verified",
                "role": "owner",
                "subtype": "email",
                "value_hash": "owner_email_b",
                "value_for_private_note": "SAMPLE_OWNER_B_EMAIL",
            },
        ]
        result = registry.evaluate_fact_slot_resolution(slots)
        self.assertFalse(result["ok"])
        self.assertIn("owner_conflict", {row["check"] for row in result["findings"]})

    def test_admin_programming_code_must_be_distinct_from_guest_code(self) -> None:
        slots = registry.sample_fact_slots()
        for slot in slots:
            if slot["slot_id"] in {"access.guest_door_code", "access.programming_admin_code"}:
                slot["value_hash"] = "same_code_hash"
        result = registry.evaluate_fact_slot_resolution(slots)
        self.assertFalse(result["ok"])
        self.assertIn("access_code_separation", {row["check"] for row in result["findings"]})

    def test_missing_phone_stays_needs_confirmation(self) -> None:
        slots = registry.sample_fact_slots()
        slots.append(
            {
                "slot_id": "contact.owner.phone",
                "section": "Contacts",
                "label": "MISSING - owner phone",
                "state": "missing_after_full_sweep",
                "role": "owner",
                "subtype": "phone",
                "required": True,
            }
        )
        result = registry.evaluate_fact_slot_resolution(slots)
        self.assertFalse(result["ok"])
        self.assertIn("needs_confirmation_placement", {row["check"] for row in result["findings"]})

    def test_cleaner_and_owner_cannot_collapse(self) -> None:
        slots = registry.sample_fact_slots()
        for slot in slots:
            if slot.get("role") in {"owner", "cleaner"}:
                slot["value_hash"] = "same_person"
        result = registry.evaluate_fact_slot_resolution(slots)
        self.assertFalse(result["ok"])
        self.assertIn("cleaner_owner_separation", {row["check"] for row in result["findings"]})


class ProductBoundaryTests(unittest.TestCase):
    def test_split_private_and_public_products(self) -> None:
        private_body = registry.build_private_operations_note("sample_property")
        public_artifact = registry.build_public_audit_artifact("sample_property")
        self.assertTrue(semantic.evaluate_body(private_body)["ok"])
        self.assertTrue(semantic.evaluate_public_redaction_gate(public_artifact)["ok"])
        self.assertIn("Gate Summary", public_artifact)
        self.assertNotIn("Gate Summary", private_body)

    def test_public_artifact_rejects_private_values(self) -> None:
        result = semantic.evaluate_public_redaction_gate("Guest access value SAMPLE_GUEST_ACCESS_VALUE\nWireless secret SAMPLE_WIFI_SECRET")
        self.assertFalse(result["ok"])
        self.assertIn("public_redaction_gate", {row["check"] for row in result["findings"]})


class FreshReplaceModelTests(unittest.TestCase):
    def identity(self) -> fresh_replace.PropertyIdentity:
        return fresh_replace.PropertyIdentity(
            property_id="sample_property",
            title="123 Example St, Sample City, ST 00000 - Deluxe Dossier",
            marker="sample_property",
            address="123 Example St",
            name="Sample Property",
        )

    def note(self, note_id: str = "old-note") -> dict[str, str]:
        return {
            "id": note_id,
            "title": "123 Example St, Sample City, ST 00000 - Deluxe Dossier",
            "folder": "STR Property Information",
            "body": "Sample Property at 123 Example St sample_property.",
            "property_marker": "sample_property",
            "address": "123 Example St",
            "name": "Sample Property",
        }

    def test_duplicate_active_note_blocks_publish(self) -> None:
        notes = [self.note("old-1"), self.note("old-2")]
        result = fresh_replace.precheck_duplicate_matching(notes, self.identity())
        self.assertFalse(result["ok"])
        self.assertEqual(result["match_count"], 2)

    def test_archive_proof_and_live_readback_required(self) -> None:
        result = fresh_replace.simulate_fresh_replace_property_information_note(
            identity=self.identity(),
            notes_before=[self.note()],
            replacement_body=GOOD_BODY,
            live_readback_body=None,
            public_closeout_text=GOOD_CLOSEOUT,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["archive_proof"]["ok"])
        self.assertTrue(result["old_id_no_longer_active"])
        self.assertIn("live_readback_required", {row["check"] for row in result["findings"]})

    def test_success_requires_readback_semantic_gate_and_public_redaction_gate(self) -> None:
        result = fresh_replace.simulate_fresh_replace_property_information_note(
            identity=self.identity(),
            notes_before=[self.note()],
            replacement_body=GOOD_BODY,
            live_readback_body=GOOD_BODY,
            public_closeout_text=GOOD_CLOSEOUT,
        )
        self.assertTrue(result["ok"], result["findings"])
        self.assertTrue(result["readback_semantic_gate"]["ok"])
        self.assertTrue(result["public_redaction_gate"]["ok"])
        self.assertFalse(result["mutated_live_apple_notes"])


if __name__ == "__main__":
    unittest.main()
