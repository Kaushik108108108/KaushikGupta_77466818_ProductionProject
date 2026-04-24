# ScholarAI ML integration notes

This project has been updated so that both `admin` and `student` prediction flows use the same shared ML workflow in `app/ml_service.py`.

## What changed
- Added `app/ml_service.py` for shared prediction, trend, risk, grading, artifact loading, and DB upsert helpers.
- Added `app/artifacts/` with bootstrap model files and JSON metadata/rules.
- Updated `app/routes/admin.py` to use the shared ML service and save complaint/dues snapshots correctly.
- Updated `app/routes/student.py` to use the same ML workflow as admin.
- Synced prediction outputs to both `predictions` and `student_academic_records`, and updated `students.performance_index`, `students.risk_level`, and related summary fields.
- Added Colab notebooks under `ml/` for KaggleHub-based training and Flask integration.
- Updated `requirements.txt` with runtime ML dependencies.

## Important
The bundled model in `app/artifacts/` is a bootstrap demo model so the code runs immediately.
For your final project submission, replace it with the Kaggle-trained artifacts exported by the Colab notebook using the same filenames.
