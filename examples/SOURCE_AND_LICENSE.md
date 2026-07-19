# Fixed Sample Source and License

`sample_raw_epoch.csv` is a de-identified, derived 30-second feature table from the public Sleep-Accel dataset. The source subject identifier and PSG stage labels are not included in the web sample.

Source:

Walch O. Motion and heart rate from a wrist-worn wearable and labeled sleep from polysomnography. Version 1.0.0. PhysioNet; 2019. DOI: https://doi.org/10.13026/hmhs-py35

Source license:

Open Data Commons Attribution License v1.0 (ODC-By). The official license text downloaded from PhysioNet is saved as `Sleep-Accel_LICENSE.txt` in this folder.

Transformation for this prototype:

- Aggregated wearable measurements are represented as nine 30-second epoch features.
- The source `subject_id` column was removed.
- No PSG reference label is included.
- No random or synthetic value was added.

This attribution must remain with any public deployment or redistribution of the fixed sample.
