# Model training

The production classifier must be trained from labelled rows, not from URL text
patterns. Each row should contain the `evidence-v1` feature columns generated
by `FeatureExtractor` and a `label` column (`1` phishing, `0` benign).

Use separate time-based train/validation/test splits so that URLs from the same
campaign do not leak across splits. Report precision, recall, F1, ROC-AUC, and
false-positive rate before promoting a model.

`train.py` is a reproducible starting point. It is intentionally not run until
a lawful, labelled dataset is supplied.
