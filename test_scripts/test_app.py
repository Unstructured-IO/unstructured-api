import httpx
import pandas as pd
import io
from pathlib import Path

MAIN_API_ROUTE = "general/v0/general"
BASE_URL = "http://127.0.0.1:6989"  # Replace with your actual API base URL

def test_general_api():
    # List of test cases
    test_cases = [
        # PASS
        ("stanley-cups.csv", "application/csv"),
        ("fake.doc", "application/msword"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("family-day.eml", "message/rfc822"),
        ("alert.eml", "message/rfc822"),
        ("announcement.eml", "message/rfc822"),
        ("fake-email-attachment.eml", "message/rfc822"),
        ("fake-email-image-embedded.eml", "message/rfc822"),
        ("fake-email.eml", "message/rfc822"),
        ("winter-sports.epub", "application/epub"), # Fix tempfile issue
        # PASS
        ("fake-html.html", "text/html"),
        ("layout-parser-paper-fast.jpg", "image/jpeg"), # Fix tempfile issue, install tesseract, poppler
        # PASS
        ("spring-weather.html.json", "application/json"),
        ("README.md", "text/markdown"),
        ("fake-email.msg", "application/x-ole-storage"),
        ("fake.odt", "application/vnd.oasis.opendocument.text"), # install pandoc
        # ("layout-parser-paper.pdf", "application/pdf"), # install tesseract and poppler
        ("fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        ("fake-power-point.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("README.rst", "text/x-rst"), # fix tempfile issue
        ("fake-doc.rtf", "application/rtf"), # fix tempfile issue
        ("fake-text.txt", "text/plain"),
        ("stanley-cups.tsv", "text/tsv"),
        ("stanley-cups.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("fake-xml.xml", "application/xml"),
    ]

    for test_id, (example_filename, content_type) in enumerate(test_cases):

        # print(f"Test Case {test_id}: {example_filename} - {content_type}")
        test_file = Path("sample-docs") / example_filename

        try:

            with httpx.Client(base_url=BASE_URL, timeout=None) as client:
                # Single file test
                with open(test_file, "rb") as file:
                    response = client.post(
                        MAIN_API_ROUTE,
                        files={"files": (str(test_file), file, content_type)}
                    )

                assert response.status_code == 200
                json_response = response.json()
                assert len(json_response) > 0
                for i in json_response:
                    assert i["metadata"]["filename"] == example_filename
                assert len("".join(elem["text"] for elem in json_response)) > 20

                # Multiple files test
                with open(test_file, "rb") as file1, open(test_file, "rb") as file2:
                    response = client.post(
                        MAIN_API_ROUTE,
                        files=[
                            ("files", (str(test_file), file1, content_type)),
                            ("files", (str(test_file), file2, content_type)),
                        ]
                    )

                assert response.status_code == 200
                json_response = response.json()
                assert all(x["metadata"]["filename"] == example_filename for i in json_response for x in i)
                assert len(json_response) > 0

                # CSV output test
                with open(test_file, "rb") as file1, open(test_file, "rb") as file2:
                    csv_response = client.post(
                        MAIN_API_ROUTE,
                        files=[
                            ("files", (str(test_file), file1, content_type)),
                            ("files", (str(test_file), file2, content_type)),
                        ],
                        data={"output_format": "text/csv"}
                    )

                assert csv_response.status_code == 200
                dfs = pd.read_csv(io.StringIO(csv_response.text))
                assert len(dfs) > 0

            print(f"Test passed for {example_filename}")
        except Exception as e:
            print(f"Failed Test Case {test_id}: {example_filename} - {content_type}")

if __name__ == "__main__":
    test_general_api()