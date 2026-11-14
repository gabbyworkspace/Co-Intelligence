"""G's final decision by verified email reply (optional channel)."""
from coint.email_decisions import gmail_authenticated, new_text, parse_decision, process_email_decisions
from coint.email_report import process_email_outbox

GOOD_AUTH = ("Authentication-Results", "mx.google.com; dkim=pass header.i=@resystem.org; spf=pass; "
             "dmarc=pass (p=REJECT) header.from=resystem.org")


def _review_mid(h):
    return h.db.one("SELECT rfc822_message_id FROM email_outbox WHERE kind='review_package'")["rfc822_message_id"]


def _reply(h, mid, body, sender="G <g@resystem.org>", auth=GOOD_AUTH, refs=None):
    headers = [auth] if auth else []
    headers += [("From", sender), ("Message-ID", f"<{mid}@mail.example>"),
                ("In-Reply-To", refs if refs is not None else _review_mid(h)),
                ("Subject", "Re: [Review Required] CI-TEST")]
    h.gmail.inbox[mid] = {"headers": headers, "body": body}


def test_parse_and_quote_stripping():
    text = new_text("APPROVE AND CLOSE\n\nOn Sat, Nov 14 JARVIS wrote:\n> REQUEST CHANGES\n")
    assert parse_decision(text) == {"decision_type": "delivery_approve_close"}
    d = parse_decision("REQUEST CHANGES\nRoute: development\n- make button blue\n- fix typo")
    assert d["route"] == "development" and d["changes"] == ["make button blue", "fix typo"]
    for bad in ("looks good, go ahead", "APPROVE AND CLOSE and REQUEST CHANGES", "REQUEST CHANGES\n- x"):
        try:
            parse_decision(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


def test_gmail_authentication_header_rules():
    assert gmail_authenticated([GOOD_AUTH], "g@resystem.org")
    forged = ("Authentication-Results", "evil.example; dmarc=pass")
    assert not gmail_authenticated([forged, GOOD_AUTH], "g@resystem.org")      # top-most must be Gmail's
    assert not gmail_authenticated([("Authentication-Results", "mx.google.com; dkim=fail; dmarc=fail")],
                                   "g@resystem.org")


def test_email_approval_closes_and_sends_final_report(h):
    h.to_final_review()
    _reply(h, "m1", "APPROVE AND CLOSE\n\nThanks.\n\nOn Sat JARVIS wrote:\n> [Review Required] ...")
    assert process_email_decisions(h.engine) == {"m1": "accepted"}
    assert h.project()["stage"] == "FOUNDER_DECISION_REFERENCE" and h.project()["status"] == "ACTIVE"
    h.run_all()          # JARVIS reference -> KITT record -> closure
    assert h.project()["status"] == "CLOSED"
    assert list(process_email_outbox(h.engine).values()) == ["sent"]
    final = h.gmail.sends[-1]
    assert final["To"] == "g@resystem.org" and final["Subject"].startswith("[Project Closed]")
    assert process_email_decisions(h.engine) == {}          # each email examined once


def test_email_request_changes_starts_new_version(h):
    h.to_final_review()
    _reply(h, "m2", "REQUEST CHANGES\nRoute: development\n- make the button larger")
    assert process_email_decisions(h.engine) == {"m2": "accepted"}
    h.run_all()
    assert h.project()["current_cycle"] == 2 and h.final_count() == 0


def test_email_rejections(h):
    h.to_final_review()
    _reply(h, "s1", "APPROVE AND CLOSE", sender="Mallory <mallory@evil.example>")
    _reply(h, "s2", "APPROVE AND CLOSE", auth=("Authentication-Results", "mx.google.com; dkim=fail; dmarc=fail"))
    _reply(h, "s3", "APPROVE AND CLOSE", refs="<unrelated@x>")
    _reply(h, "s4", "looks good, go ahead")
    _reply(h, "s5", "APPROVE AND CLOSE", auth=None)
    out = process_email_decisions(h.engine)
    assert out == {"s1": "ignored", "s2": "rejected", "s3": "rejected", "s4": "ignored", "s5": "rejected"}
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW" and h.final_count() == 0


def test_email_bound_by_explicit_version_when_not_threaded(h):
    h.to_final_review()
    sha = h.project()["current_delivery_sha"]
    _reply(h, "m3", f"APPROVE AND CLOSE CI-TEST v1 {sha}", refs="")
    assert process_email_decisions(h.engine) == {"m3": "accepted"}


def test_stale_email_after_new_version_rejected(h):
    h.to_final_review()
    old_mid = _review_mid(h)
    _reply(h, "m4", "REQUEST CHANGES\nRoute: development\n- x")
    process_email_decisions(h.engine)
    h.run_all()
    process_email_outbox(h.engine)                        # Version 2 review package
    _reply(h, "m5", "APPROVE AND CLOSE", refs=old_mid)     # replies to the Version 1 package
    assert process_email_decisions(h.engine) == {"m5": "rejected"}
    assert h.project()["status"] == "ACTIVE"


def test_email_channel_disabled(make_h):
    h = make_h(email_decisions_enabled=False)
    h.to_final_review()
    _reply(h, "m6", "APPROVE AND CLOSE")
    assert "skipped" in process_email_decisions(h.engine)


def test_short_close_reply_from_baileys_in_thread_closes(h):
    """G 2026-11-14: 'close' from g@ or baileys@, in the review thread, counts as APPROVE AND CLOSE."""
    h.to_final_review()
    baileys_auth = ("Authentication-Results", "mx.google.com; dkim=pass header.i=@gmail.com; spf=pass; "
                    "dmarc=pass (p=NONE) header.from=gmail.com")
    _reply(h, "c1", "close\n\nOn Sat JARVIS wrote:\n> [Review Required] ...",
           sender="Baileys <baileys.resystem@gmail.com>", auth=baileys_auth)
    assert process_email_decisions(h.engine) == {"c1": "accepted"}
    h.run_all()
    assert h.project()["status"] == "CLOSED"


def test_short_close_needs_thread_and_mixed_text_ignored(h):
    h.to_final_review()
    _reply(h, "c2", "close", refs="")                       # not in the review thread
    _reply(h, "c3", "close it but also change the colour")  # not a short close reply
    assert process_email_decisions(h.engine) == {"c2": "rejected", "c3": "ignored"}
    assert h.project()["status"] == "ACTIVE"
