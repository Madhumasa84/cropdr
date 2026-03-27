class PredictionCandidate {
  const PredictionCandidate({
    required this.label,
    required this.confidence,
  });

  final String label;
  final double confidence;

  factory PredictionCandidate.fromJson(Map<String, dynamic> json) {
    return PredictionCandidate(
      label: (json['label'] ?? 'Unknown').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    );
  }
}

class TreatmentRecommendation {
  const TreatmentRecommendation({
    required this.chemical,
    required this.organic,
    required this.dosage,
    required this.frequency,
    required this.prevention,
    required this.source,
  });

  final String chemical;
  final String organic;
  final String dosage;
  final String frequency;
  final List<String> prevention;
  final String source;

  factory TreatmentRecommendation.fromJson(Map<String, dynamic> json) {
    final preventionRaw = json['prevention'];
    return TreatmentRecommendation(
      chemical: (json['chemical'] ?? 'Consult a local agronomist before spraying.').toString(),
      organic: (json['organic'] ?? 'Use a supportive organic spray and continue scouting.').toString(),
      dosage: (json['dosage'] ?? 'Follow the label recommendation.').toString(),
      frequency: (json['frequency'] ?? 'Monitor weekly.').toString(),
      prevention: preventionRaw is List
          ? preventionRaw.map((item) => item.toString()).toList()
          : const [],
      source: (json['source'] ?? 'backend').toString(),
    );
  }
}

class AdvisorySummary {
  const AdvisorySummary({
    required this.nextStep,
    required this.farmerMessage,
  });

  final String nextStep;
  final String farmerMessage;

  factory AdvisorySummary.fromJson(Map<String, dynamic> json) {
    return AdvisorySummary(
      nextStep: (json['next_step'] ?? 'Keep monitoring your crop.').toString(),
      farmerMessage: (json['farmer_message'] ?? '').toString(),
    );
  }
}

class ScanResult {
  const ScanResult({
    required this.crop,
    required this.disease,
    required this.label,
    required this.confidence,
    required this.severity,
    required this.lesionRatio,
    required this.treatment,
    required this.topPredictions,
    this.advisory,
  });

  final String crop;
  final String disease;
  final String label;
  final double confidence;
  final String severity;
  final double lesionRatio;
  final TreatmentRecommendation treatment;
  final List<PredictionCandidate> topPredictions;
  final AdvisorySummary? advisory;

  factory ScanResult.fromJson(Map<String, dynamic> json) {
    final predictionsRaw = json['top_predictions'];
    return ScanResult(
      crop: (json['crop'] ?? 'Unknown').toString(),
      disease: (json['disease'] ?? 'Unknown').toString(),
      label: (json['label'] ?? 'Unknown').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      severity: (json['severity'] ?? 'LOW').toString(),
      lesionRatio: (json['lesion_ratio'] as num?)?.toDouble() ?? 0,
      treatment: TreatmentRecommendation.fromJson(
        (json['treatment'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
      ),
      topPredictions: predictionsRaw is List
          ? predictionsRaw
              .whereType<Map<String, dynamic>>()
              .map(PredictionCandidate.fromJson)
              .toList()
          : const [],
      advisory: json['advisory'] is Map<String, dynamic>
          ? AdvisorySummary.fromJson(json['advisory'] as Map<String, dynamic>)
          : null,
    );
  }
}

class WeatherSummary {
  const WeatherSummary({
    required this.tempAvg,
    required this.humidityAvg,
    required this.rainfall7dayMm,
  });

  final double tempAvg;
  final double humidityAvg;
  final double rainfall7dayMm;

  factory WeatherSummary.fromJson(Map<String, dynamic> json) {
    return WeatherSummary(
      tempAvg: (json['temp_avg'] as num?)?.toDouble() ?? 0,
      humidityAvg: (json['humidity_avg'] as num?)?.toDouble() ?? 0,
      rainfall7dayMm: (json['rainfall_7day_mm'] as num?)?.toDouble() ?? 0,
    );
  }
}

class WeatherSnapshot {
  const WeatherSnapshot({
    required this.temp,
    required this.humidity,
    required this.description,
  });

  final double temp;
  final double humidity;
  final String description;

  factory WeatherSnapshot.fromJson(Map<String, dynamic> json) {
    return WeatherSnapshot(
      temp: (json['temp'] as num?)?.toDouble() ?? 0,
      humidity: (json['humidity'] as num?)?.toDouble() ?? 0,
      description: (json['description'] ?? '').toString(),
    );
  }
}

class WeatherCoordinates {
  const WeatherCoordinates({
    required this.latitude,
    required this.longitude,
  });

  final double latitude;
  final double longitude;

  factory WeatherCoordinates.fromJson(Map<String, dynamic> json) {
    return WeatherCoordinates(
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0,
    );
  }
}

class WeatherRiskItem {
  const WeatherRiskItem({
    required this.disease,
    required this.riskLevel,
    required this.confidence,
    required this.preventionTip,
    required this.urgencyDays,
  });

  final String disease;
  final String riskLevel;
  final double confidence;
  final String preventionTip;
  final int urgencyDays;

  factory WeatherRiskItem.fromJson(Map<String, dynamic> json) {
    return WeatherRiskItem(
      disease: (json['disease'] ?? 'Unknown').toString(),
      riskLevel: (json['risk_level'] ?? 'LOW').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      preventionTip: (json['prevention_tip'] ?? 'Keep scouting your crop.').toString(),
      urgencyDays: (json['urgency_days'] as num?)?.toInt() ?? 0,
    );
  }
}

class WeatherRiskResult {
  const WeatherRiskResult({
    required this.crop,
    required this.location,
    required this.predictionDate,
    required this.weatherSummary,
    required this.cropStage,
    required this.risks,
    required this.modelVersion,
    this.currentSnapshot,
    this.coordinates,
    this.source,
  });

  final String crop;
  final String location;
  final String predictionDate;
  final WeatherSummary weatherSummary;
  final String cropStage;
  final List<WeatherRiskItem> risks;
  final String modelVersion;
  final WeatherSnapshot? currentSnapshot;
  final WeatherCoordinates? coordinates;
  final String? source;

  factory WeatherRiskResult.fromJson(Map<String, dynamic> json) {
    final risksRaw = json['risks'];
    return WeatherRiskResult(
      crop: (json['crop'] ?? 'Unknown').toString(),
      location: (json['location'] ?? 'Unknown').toString(),
      predictionDate: (json['prediction_date'] ?? '').toString(),
      weatherSummary: WeatherSummary.fromJson(
        (json['weather_summary'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
      ),
      cropStage: (json['crop_stage'] ?? 'General').toString(),
      risks: risksRaw is List
          ? risksRaw
              .whereType<Map<String, dynamic>>()
              .map(WeatherRiskItem.fromJson)
              .toList()
          : const [],
      modelVersion: (json['model_version'] ?? 'unknown').toString(),
      currentSnapshot: json['current_snapshot'] is Map<String, dynamic>
          ? WeatherSnapshot.fromJson(json['current_snapshot'] as Map<String, dynamic>)
          : null,
      coordinates: json['coordinates'] is Map<String, dynamic>
          ? WeatherCoordinates.fromJson(json['coordinates'] as Map<String, dynamic>)
          : null,
      source: json['source']?.toString(),
    );
  }
}
