from fastapi.testclient import TestClient

from unstructured_api_tools.pipelines.api_conventions import get_pipeline_path


from prepline_general.api.app import app

MAIN_API_ROUTE = get_pipeline_path("general")


def test_general_api_health_check():
    client = TestClient(app)
    response = client.get("/healthcheck")

    assert response.status_code == 200


# layout-parser-paper.pdf
# layout-parser-paper-fast.jpg
# fake.doc
# fake-power-point.ppt
# family-day.eml
# fake.docx
# fake-text.txt
# fake-power-point.pptx
# fake-html.html
# fake-excel.xlsx
# fake-email.eml
# fake-email-image-embedded.eml
# fake-email-attachment.eml
# announcement.eml
# alert.eml


def test_general_api_health_check():
    client = TestClient(app)

    # NOTE(robinson) - Reset the rate limit to avoid 429s in tests
    app.state.limiter.reset()
    client = TestClient(app)
    response = client.post(
        SECTION_ROUTE,
        files=[("text_files", (filename, open(filename, "rb"), "text/plain"))],
        data={"output_schema": "labelstudio", "section": [section]},
    )
