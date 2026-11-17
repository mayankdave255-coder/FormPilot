"""Backend API tests. Run from the project root with: python -m pytest -q"""
import io
import fitz
import pytest
import uuid
from fastapi.testclient import TestClient

from backend import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def signed_in_user():
    email = f"{uuid.uuid4().hex}@example.test"
    response = client.post("/api/v1/auth/signup", json={"name":"Test User", "email":email, "password":"Correct-Horse-42!"})
    assert response.status_code == 200, response.text
    yield {"email": email, "password": "Correct-Horse-42!"}
    client.post("/api/v1/auth/logout")


def test_auth_required_and_session_isolation():
    anonymous = TestClient(main.app)
    assert anonymous.get("/api/v1/sessions").status_code == 401
    created = client.post("/api/v1/sessions", json={}).json()
    other = TestClient(main.app)
    other.post("/api/v1/auth/signup", json={"name":"Other User", "email":f"{uuid.uuid4().hex}@example.test", "password":"Correct-Horse-42!"})
    assert other.get(f"/api/v1/sessions/{created['session_id']}").status_code == 404
    assert other.delete(f"/api/v1/sessions/{created['session_id']}").status_code == 404
    assert client.delete(f"/api/v1/sessions/{created['session_id']}").status_code == 200


def test_signup_validation_and_login(signed_in_user):
    assert client.post("/api/v1/auth/login", json={"email":"unknown@example.test", "password":"wrong"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
    result = client.post("/api/v1/auth/login", json=signed_in_user)
    assert result.status_code == 200
    assert client.get("/api/v1/auth/me").json()["user"]["email"] == signed_in_user["email"]


def test_session_data_is_persisted(sid):
    path = main.SESSION_STORE_DIR / f"{sid}.json"
    assert path.exists()
    saved = path.read_text(encoding="utf-8")
    assert '"owner_id"' in saved
    client.delete(f"/api/v1/sessions/{sid}")
    assert not path.exists()


def make_pdf(lines: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 18
    data = doc.tobytes()
    doc.close()
    return data


APPLICATION_PDF = make_pdf([
    "National Scholarship Application",
    "Full name as per official record: ",
    "Date of birth: ",
    "Annual household income: ",
    "Bank account holder name: ",
    "Email address: ",
])
MARKSHEET_PDF = make_pdf(["Class 12 Marksheet", "Student Name: Rahul Kumar", "Result: Passed"])
INCOME_PDF = make_pdf(["Income Certificate", "Annual family income: Rs. 300,000"])


@pytest.fixture()
def sid():
    r = client.post("/api/v1/sessions", json={})
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    yield session_id
    client.delete(f"/api/v1/sessions/{session_id}")


def upload(sid, name, content, kind="supporting", mime="application/pdf"):
    return client.post(f"/api/v1/applications/{sid}/documents",
                       files={"file": (name, io.BytesIO(content), mime)},
                       data={"document_kind": kind, "language": "en"})


def upload_and_process(sid, name, content, kind="supporting", mime="application/pdf"):
    r = upload(sid, name, content, kind, mime)
    assert r.status_code == 200, r.text
    doc_id = r.json()["document_id"]
    p = client.post(f"/api/v1/documents/{doc_id}/process", json={"language": "en"})
    assert p.status_code == 200
    d = client.get(f"/api/v1/documents/{doc_id}").json()
    assert d["processing_status"] == "completed", d
    return doc_id


# ---- health and sessions -------------------------------------------------

def test_health_demo_mode():
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["mode"] in {"demo", "live"}


def test_session_lifecycle():
    sid = client.post("/api/v1/sessions", json={"preferred_language": "xx"}).json()["session_id"]
    s = client.get(f"/api/v1/sessions/{sid}").json()
    assert s["preferred_language"] == "en"  # unknown language falls back
    assert client.delete(f"/api/v1/sessions/{sid}").json()["deleted"] is True
    r = client.get(f"/api/v1/sessions/{sid}")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "session_not_found"


# ---- upload validation ---------------------------------------------------

def test_upload_rejects_wrong_type(sid):
    r = upload(sid, "x.txt", b"hello", mime="text/plain")
    assert r.status_code == 415


def test_upload_rejects_empty_and_fake_pdf(sid):
    assert upload(sid, "a.pdf", b"").status_code == 422
    assert upload(sid, "a.pdf", b"not a pdf").status_code == 422


def test_upload_rejects_fake_png_and_jpeg(sid):
    assert upload(sid, "a.png", b"junk", mime="image/png").status_code == 422
    assert upload(sid, "a.jpg", b"junk", mime="image/jpeg").status_code == 422


def test_upload_too_large(sid, monkeypatch):
    monkeypatch.setattr(main, "MAX_FILE_MB", 0)
    assert upload(sid, "a.pdf", APPLICATION_PDF).status_code == 413


def test_upload_unknown_session():
    r = client.post("/api/v1/applications/nope/documents",
                    files={"file": ("a.pdf", io.BytesIO(APPLICATION_PDF), "application/pdf")})
    assert r.status_code == 404


def test_pdf_page_limit(sid, monkeypatch):
    monkeypatch.setattr(main, "MAX_PDF_PAGES", 1)
    two = fitz.open(); two.new_page(); two.new_page(); data = two.tobytes()
    doc_id = upload(sid, "big.pdf", data).json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process", json={})
    d = client.get(f"/api/v1/documents/{doc_id}").json()
    assert d["processing_status"] == "failed"


# ---- extraction and schema -----------------------------------------------

def test_schema_from_uploaded_application(sid):
    upload_and_process(sid, "form.pdf", APPLICATION_PDF, kind="application")
    schema = client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []}).json()
    labels = [f["label_original"].lower() for f in schema["fields"]]
    assert schema["status"] == "ready"
    assert any("income" in l for l in labels) and any("email" in l for l in labels)


def test_schema_falls_back_to_sample_without_document(sid):
    schema = client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []}).json()
    assert schema["field_count"] == len(main.SAMPLE_FIELDS)


def test_image_without_provider_completes_with_no_text(sid):
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (40, 40), "white").save(buf, "PNG")
    doc_id = upload_and_process(sid, "scan.png", buf.getvalue(), kind="application", mime="image/png")
    assert client.get(f"/api/v1/documents/{doc_id}").json()["text_available"] is False


def test_delete_document(sid):
    doc_id = upload(sid, "m.pdf", MARKSHEET_PDF).json()["document_id"]
    assert client.delete(f"/api/v1/applications/{sid}/documents/{doc_id}").json()["deleted"]
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 404


# ---- answers, validation, evidence ---------------------------------------

def answer(sid, field_id, value, confirmed=True):
    return client.post(f"/api/v1/applications/{sid}/answers",
                       json={"field_id": field_id, "value": value, "confirmed": confirmed})


def test_unknown_field_rejected(sid):
    assert answer(sid, "does_not_exist", "x").status_code == 404


def test_validation_reports_required_fields_even_before_schema(sid):
    issues = client.post(f"/api/v1/applications/{sid}/validate", json={}).json()["issues"]
    ids = {i["id"] for i in issues}
    assert "missing_full_name" in ids, "sample required fields should be checked in demo mode"


def test_missing_income_certificate_then_added(sid):
    ids = {i["id"] for i in client.post(f"/api/v1/applications/{sid}/validate", json={}).json()["issues"]}
    assert "missing_income_certificate" in ids
    upload_and_process(sid, "income.pdf", INCOME_PDF, kind="income_certificate")
    ids = {i["id"] for i in client.post(f"/api/v1/applications/{sid}/validate", json={}).json()["issues"]}
    assert "missing_income_certificate" not in ids


def test_invalid_email(sid):
    client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []})
    answer(sid, "email", "not-an-email")
    ids = {i["id"] for i in client.post(f"/api/v1/applications/{sid}/validate", json={}).json()["issues"]}
    assert "invalid_email" in ids


def test_unconfirmed_answer_needs_review(sid):
    answer(sid, "gender", "Male", confirmed=False)
    ids = {i["id"] for i in client.post(f"/api/v1/applications/{sid}/validate", json={}).json()["issues"]}
    assert "confirm_gender" in ids


def test_name_mismatch_detected_and_resolvable(sid):
    upload_and_process(sid, "marksheet.pdf", MARKSHEET_PDF)
    ev = client.post(f"/api/v1/applications/{sid}/evidence-match").json()
    assert any(c["field_id"] == "full_name" and c["value"] == "Rahul Kumar" for c in ev["candidates"])
    answer(sid, "full_name", "Rahul K.")
    ids = {i["id"] for i in client.get(f"/api/v1/applications/{sid}/readiness").json()["issues"]}
    assert "name_mismatch" in ids
    client.post(f"/api/v1/applications/{sid}/issues/name_mismatch/resolve")
    ids = {i["id"] for i in client.get(f"/api/v1/applications/{sid}/readiness").json()["issues"]}
    assert "name_mismatch" not in ids


def test_matching_name_has_no_mismatch(sid):
    upload_and_process(sid, "marksheet.pdf", MARKSHEET_PDF)
    answer(sid, "full_name", "  rahul   KUMAR ")
    ids = {i["id"] for i in client.get(f"/api/v1/applications/{sid}/readiness").json()["issues"]}
    assert "name_mismatch" not in ids


# ---- explain / conversation / voice --------------------------------------

def test_explain_field_demo_languages(sid):
    client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []})
    en = client.post(f"/api/v1/fields/annual_household_income/explain?application_id={sid}", json={"language": "en"}).json()
    hi = client.post(f"/api/v1/fields/annual_household_income/explain?application_id={sid}", json={"language": "hi"}).json()
    assert en["provider"] == "demo" and hi["explanation"] != en["explanation"]


def test_conversation_never_saves_answer(sid):
    client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []})
    r = client.post(f"/api/v1/applications/{sid}/conversation", json={"field_id": "annual_household_income", "text": "3 lakh", "language": "en"}).json()
    assert r["answer_saved"] is False and "3 lakh" in r["assistant_turn"]["text"]


def test_voice_unavailable_without_keys():
    if main.SARVAM_API_KEY:
        pytest.skip("provider key configured")
    t = client.post("/api/v1/voice/transcribe", files={"file": ("a.webm", io.BytesIO(b"abc"), "audio/webm")})
    s = client.post("/api/v1/voice/synthesize", json={"text": "hi"})
    assert t.status_code == 503 and s.status_code == 503


# ---- export and draft ----------------------------------------------------

def test_export_and_draft_pdf(sid):
    client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []})
    answer(sid, "full_name", "Rahul Kumar")
    export = client.get(f"/api/v1/applications/{sid}/answers/export").json()
    assert export["submitted"] is False
    assert next(a for a in export["answers"] if a["field_id"] == "full_name")["value"] == "Rahul Kumar"
    draft = client.post(f"/api/v1/applications/{sid}/draft", json={}).json()
    pdf = client.get(draft["download_url"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    text = fitz.open(stream=pdf.content, filetype="pdf")[0].get_text()
    assert "Rahul Kumar" in text


def test_draft_renders_hindi_answer(sid):
    client.post(f"/api/v1/applications/{sid}/form-schema", json={"document_ids": []})
    answer(sid, "residential_address", "भोपाल, मध्य प्रदेश")
    draft = client.post(f"/api/v1/applications/{sid}/draft", json={}).json()
    pdf = client.get(draft["download_url"]).content
    text = "".join(p.get_text() for p in fitz.open(stream=pdf, filetype="pdf"))
    assert "भोपाल" in text, "Devanagari must survive in the draft PDF, not turn into '?'"


def test_draft_unknown_id(sid):
    assert client.get(f"/api/v1/applications/{sid}/drafts/nope").status_code == 404


# ---- static serving / security -------------------------------------------

def test_frontend_files_served():
    for path in ["/", "/app.js", "/styles.css"]:
        assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", [
    "/.env", "/.env.example", "/backend/main.py", "/Dockerfile", "/docker-compose.yml",
    "/requirements.txt", "/README.md", "/run.ps1", "/.gitignore", "/../backend/main.py",
])
def test_private_files_not_served(path):
    assert client.get(path).status_code == 404, f"{path} should not be downloadable"


def test_uploaded_documents_not_served_statically(sid):
    doc = upload(sid, "m.pdf", MARKSHEET_PDF).json()
    stored = next((main.DATA_DIR / sid).iterdir()).name
    rel = (main.DATA_DIR / sid / stored).relative_to(main.ROOT).as_posix()
    assert client.get("/" + rel).status_code == 404, "other users' uploads must not be readable by path"
