# Crop Disease Prediction Platform

Production-oriented Phase 1 project for India with:

- Model 1: PyTorch image-based leaf disease classification with ONNX export
- Model 2: teammate integration bridge
- Model 3: weather-based disease risk prediction using a rule engine and XGBoost-ready pipeline
- FastAPI backend for mobile and web clients
- Flutter app scaffold

## Backend Quick Start

From `backend/`:

```powershell
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

## Training Flow

```powershell
python src/preprocessing/label_unifier.py --datasets <plantvillage_dir> <plantdoc_dir> <multicrop_dir> --output-dir data/processed
python src/model1/train.py --manifest data/processed/manifest.csv --backbone mobilenet_v3
python src/model1/evaluate.py --manifest data/processed/manifest.csv
python src/model1/export_onnx.py
python src/model3/01_fetch_nasa_data.py
python src/model3/02_feature_engineering.py
python src/model3/03_train_model.py
```

## API Endpoints

- `POST /predict/image`
- `POST /predict/weather-risk`
- `POST /advisory`
