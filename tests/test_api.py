import copy


def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert body["columns"] == 2
    assert isinstance(body["id"], int) and body["id"] > 0


def test_process_and_retrieve(
    client, uploaded_dataset_id, processing_body
):
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process", json=processing_body
    )
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 1
    assert body["cleaning_report"]["rows_before"] == 5
    assert body["cleaning_report"]["rows_after"] == 3

    response = client.get(f"/datasets/{uploaded_dataset_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    records = body["data"]
    assert [r["student_id"] for r in records] == [1, 2, 5]
    assert [r["score"] for r in records] == [80, 90, 85]


def test_retrieve_missing_dataset(client):
    response = client.get("/datasets/999")
    assert response.status_code == 404


# Additional tests (ungraded)
def upload(client, data, name="sample_data.csv"):
    return client.post("/upload", files={"file": (name, data, "text/csv")})


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "version": "1.0.0"}


def test_bad_extension(client):
    assert upload(client, b"a,b\n1,2\n", "x.txt").status_code == 400


def test_empty_csv(client):
    assert upload(client, b"").status_code == 400


def test_limit(client, sample_csv_bytes):
    i = upload(client, sample_csv_bytes).json()["id"]
    body = client.get(f"/datasets/{i}?limit=2").json()
    assert len(body["data"]) == 2 and body["total_rows"] == 6
    assert body["data"][0] == {"student_id": 1, "score": "80"}
    assert client.get(f"/datasets/{i}").json()["data"][3]["score"] is None
    assert client.get(f"/datasets/{i}?limit=0").status_code == 422


def test_upload_metadata(client, sample_csv_bytes):
    assert upload(client, sample_csv_bytes).json() == {
        "id": 1, "filename": "sample_data.csv", "rows": 6, "columns": 2,
        "column_names": ["student_id", "score"],
    }


def test_process_missing(client, processing_body):
    assert client.post("/datasets/99/process", json=processing_body).status_code == 404


def test_process_exact_report(client, uploaded_dataset_id, processing_body):
    assert client.post(
        f"/datasets/{uploaded_dataset_id}/process", json=processing_body
    ).json() == {
        "id": 1, "validation_rows_removed": 1,
        "cleaning_report": {
            "rows_before": 5, "rows_after": 3, "rows_removed": 2,
            "columns_before": 2, "columns_after": 2, "columns_removed": 0,
        },
    }


def test_missing_column_unchanged(client, uploaded_dataset_id, processing_body):
    b = copy.deepcopy(processing_body)
    b["validation"]["numeric_columns"] = ["nope"]
    assert client.post(f"/datasets/{uploaded_dataset_id}/process", json=b).status_code == 400
    b["validation"] = {"required_columns": ["nope"], "numeric_columns": []}
    assert client.post(f"/datasets/{uploaded_dataset_id}/process", json=b).status_code == 400
    assert client.get(f"/datasets/{uploaded_dataset_id}").json()["total_rows"] == 6


def test_bad_outlier_method_unchanged(client, uploaded_dataset_id, processing_body):
    b = copy.deepcopy(processing_body)
    b["processing"]["outliers"] = {"enabled": True, "columns": ["score"], "method": "bogus", "threshold": 1.5}
    assert client.post(f"/datasets/{uploaded_dataset_id}/process", json=b).status_code == 400
    assert client.get(f"/datasets/{uploaded_dataset_id}").json()["total_rows"] == 6


def test_bad_axis(client, uploaded_dataset_id, processing_body):
    b = copy.deepcopy(processing_body)
    b["processing"]["missing"]["axis"] = "diag"
    assert client.post(f"/datasets/{uploaded_dataset_id}/process", json=b).status_code == 400


def test_malformed_body(client, uploaded_dataset_id):
    r = client.post(f"/datasets/{uploaded_dataset_id}/process", json={"validation": 5})
    assert r.status_code == 422


def test_request_ids(client):
    ids = []
    for path in ["/health", "/datasets/999", "/datasets/1?limit=0"]:
        r = client.get(path)
        assert len(r.headers["X-Request-ID"]) == 8
        ids.append(r.headers["X-Request-ID"])
    r = upload(client, b"a,b\n1,2\n", "x.txt")
    assert len(r.headers["X-Request-ID"]) == 8
    assert len(set(ids)) == 3
