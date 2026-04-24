# ScholarAI ML assets

- `scholarai_flask_colab_training.ipynb`: Train the academic score model in Google Colab using KaggleHub.
- `scholarai_flask_colab_integration.ipynb`: Shows how the exported artifacts map into the Flask routes.

After running the training notebook in Colab, copy these files into `app/artifacts/`:

- `scholarai_academic_score_pipeline.joblib`
- `scholarai_model_metadata.json`
- `scholarai_business_rules.json`

The Flask app is already integrated to use those filenames automatically.
