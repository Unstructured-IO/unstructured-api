import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from prepline_general.api.models.form_params import GeneralFormParams


@pytest.mark.parametrize(
    "values, expected",
    [
        (["eng,deu"], ["eng", "deu"]),
        (["eng+deu"], ["eng", "deu"]),
        (['["eng", "deu"]'], ["eng", "deu"]),
        (["eng", "deu"], ["eng", "deu"]),
        (["eng"], ["eng"]),
        (["eng,deu+fra"], ["eng,deu", "fra"]),
        (['["eng,deu", "fra+spa"]'], ["eng,deu", "fra+spa"]),
        (["eng,deu", "fra"], ["eng,deu", "fra"]),
    ],
)
@pytest.mark.parametrize("field", ["languages", "ocr_languages", "skip_infer_table_types"])
def test_form_list_syntax(field, values, expected):
    app = FastAPI()

    @app.post("/form")
    def parse_form(params: GeneralFormParams = Depends(GeneralFormParams.as_form)):
        return getattr(params, field)

    response = TestClient(app).post("/form", data={field: values})

    assert response.status_code == 200
    assert response.json() == expected
