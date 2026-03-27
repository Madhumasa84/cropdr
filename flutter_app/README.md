# Flutter App Structure

This folder contains a lightweight Flutter scaffold for integrating with the FastAPI backend.

Expected backend endpoints:

- `POST /predict/image`
- `POST /predict/weather-risk`
- `POST /advisory`

Suggested next steps:

1. Run the backend from `backend/`
2. For a physical phone, run Flutter with `--dart-define=API_BASE_URL=http://<YOUR-PC-LAN-IP>:8000`
3. Add camera, offline caching, and multilingual support in the mobile sprint
