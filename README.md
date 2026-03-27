🌿 Crop Doctor

AI-powered crop disease detection platform for Indian farmers — a 3-model system combining leaf image diagnosis, weather-based disease risk prediction, and ICAR-aligned treatment advisory.

📱 App Screens
Home Dashboard (crop selection + live weather)
Scan Leaf (camera / gallery upload)
Disease Result (confidence + severity + treatment + risk)


📌 Table of Contents
Overview
The Problem
What It Does
Architecture
Models
Datasets
Project Structure
Setup & Installation
Running the Backend
Running the Flutter App
API Reference
Model Performance
What Makes This Different
Roadmap
Team


🚀 Overview

Crop Doctor is an end-to-end AI platform that helps Indian farmers detect crop diseases early and take action before yield is lost.

It combines three AI models into a single mobile app:

Model 1 — Diagnoses disease from a leaf image
Model 2 — Provides ICAR-aligned treatment recommendations
Model 3 — Predicts disease risk using live weather data

✅ Fully working Android APK
✅ Tested on real device
✅ Real-time image + weather predictions


⚠️ The Problem

India loses ~35% of annual crop yield due to plant diseases (~₹2,400 crore/year).

Key challenges:

58% farmers lack timely expert advice
2–3 day detection delay → disease spreads to 40–60% of field
Existing apps fail in real-world conditions (trained on lab images)
No preventive, weather-based prediction tools
No ICAR-aligned localized treatment guidance
🌾 What It Does
Farmer Workflow
Select crop (Rice, Tomato, Wheat, etc.)
View live weather + disease risk
Upload leaf image
Get diagnosis + severity + treatment
View upcoming disease risks
Output per Scan
Disease name (86 classes)
Confidence score
Severity: Low / Moderate / High
Affected area %
Chemical treatment + dosage
Organic alternative
Prevention steps
Weather-based risk forecast



🏗️ Architecture


Flutter App
(Home · Scan · Result Screens)
        │
        ▼
FastAPI Backend
├── /predict/image
├── /predict/weather-risk
└── /advisory
        │
        ├── Model 1 → Image Classifier (ONNX)
        ├── Model 2 → Advisory Engine (ICAR KB)
        └── Model 3 → Weather Risk (XGBoost)


🤖 Models
Model 1 — Leaf Image Classifier
Architecture: MobileNetV3 (supports EfficientNet-B3, ResNet-50)
Format: ONNX Runtime
Classes: 86
Input: 224×224
Inference: Test-Time Augmentation (TTA)
Model 2 — Treatment Advisory
JSON-based ICAR knowledge base
Provides:
Chemical treatment
Organic alternatives
Dosage & frequency
Prevention steps
Optional LLM fallback
Model 3 — Weather Risk Predictor
Algorithm: XGBoost
Accuracy: 96.53%
Data:
NASA POWER (historical)
OpenWeatherMap (live)
Predicts disease risk before symptoms appear



📊 Datasets
Dataset	Images	Role
PlantVillage	54,306	Base training
PlantDoc	2,598	Field realism
MultiCrop Tamil Nadu	23,000+	Local ground truth
NASA POWER	—	Weather training

Final dataset: 35,275 images · 86 classes



🌍 Supported Crops
Tomato
Rice
Wheat
Cotton
Maize
Groundnut
Potato
Chilli
Sugarcane
Soybean


🏙️ Cities Covered

Chennai · Bengaluru · Hyderabad · Mumbai · Pune · Ahmedabad · Jaipur · Lucknow · Bhopal · Kolkata


📁 Project Structure
crop_disease_platform/

backend/
 ├── models/
 ├── src/
 │   ├── model1/
 │   ├── model2/
 │   ├── model3/
 │   ├── advisory/
 │   └── api/
 └── data/

flutter_app/
 └── lib/
     ├── screens/
     └── services/


⚙️ Setup & Installation
Prerequisites
Python 3.10+
Flutter 3.x
OpenWeatherMap API key
1. Clone Repo
git clone https://github.com/YOUR_USERNAME/crop-doctor.git
cd crop-doctor
2. Backend Setup
cd backend
python -m venv venv

# Activate
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
3. Environment Variables

Create .env:

OPENWEATHER_API_KEY=your_key
MODEL2_ENDPOINT=


▶️ Running Backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Swagger Docs:
👉 http://localhost:8000/docs

📱 Running Flutter App
cd flutter_app
flutter pub get
flutter run

Update API URL:

static const String _baseUrl = 'http://192.168.1.XXX:8000';


🔌 API Reference
POST /predict/image

Returns:

Disease
Confidence
Severity
Treatment
Top predictions
POST /predict/weather-risk

Returns:

Weather summary
Disease risk
Prevention tips
POST /advisory

Returns:

ICAR-based treatment plan



📈 Model Performance
Model 1
Accuracy: 48.4% (baseline)
Macro F1: 41.8%
Model 3
Accuracy: 96.53%
Precision: 94.42%
Recall: 97.33%
ROC AUC: 0.9952



🌟 What Makes This Different
Feature	Crop Doctor	Typical Apps
Data	Real + Indian	Lab only
Prediction	✔ Weather-based	✖ No
Treatment	✔ ICAR aligned	✖ Generic
Deployment	✔ Mobile app	✖ Demo only
Models	3 combined	1


🛣️ Roadmap
EfficientNet-B3 upgrade
Field evaluation improvements
Multi-language (Tamil, Hindi)
Cloud deployment (AWS / Railway)
Offline inference (ONNX mobile)
UAV / drone integration



👥 Team


Model Evaluation & Optimization
Ensemble Learning Architect
Data Science & Feature Engineering



📌 Summary

Crop Doctor is not just a detection app — it is a complete AI-driven decision support system for farmers, combining:

Diagnosis
Treatment
Prediction
into one unified platform.

