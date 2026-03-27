import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class ResultScreen extends StatefulWidget {
  const ResultScreen({
    super.key,
    required this.imageBytes,
    required this.prediction,
    this.weatherRisk,
    this.locationLabel,
    this.latitude,
    this.longitude,
  });

  final Uint8List imageBytes;
  final ScanResult prediction;
  final WeatherRiskResult? weatherRisk;
  final String? locationLabel;
  final double? latitude;
  final double? longitude;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  WeatherRiskResult? _weatherRisk;
  bool _loadingWeather = false;
  String? _weatherError;

  @override
  void initState() {
    super.initState();
    _weatherRisk = widget.weatherRisk;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadWeatherRisk();
    });
  }

  Future<void> _loadWeatherRisk() async {
    if (_loadingWeather) {
      return;
    }

    final hasLocationContext = (widget.locationLabel?.trim().isNotEmpty ?? false) ||
        widget.latitude != null ||
        widget.longitude != null;
    if (!hasLocationContext && _weatherRisk != null) {
      return;
    }

    setState(() {
      _loadingWeather = true;
      _weatherError = null;
    });

    try {
      final result = await ApiService.getWeatherRisk(
        crop: widget.prediction.crop,
        location: widget.locationLabel,
        latitude: widget.latitude,
        longitude: widget.longitude,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _weatherRisk = result;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _weatherError = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _loadingWeather = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final prediction = widget.prediction;
    final confidencePercent = (prediction.confidence * 100).clamp(0, 100).toStringAsFixed(0);
    final lesionPercent = (prediction.lesionRatio * 100).clamp(0, 100).toStringAsFixed(0);
    final risks = _weatherRisk?.risks ?? const <WeatherRiskItem>[];
    final topRisks = risks.take(3).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Result'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(28),
            child: Image.memory(
              widget.imageBytes,
              height: 220,
              width: double.infinity,
              fit: BoxFit.cover,
            ),
          ),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          prediction.crop,
                          style: const TextStyle(
                            color: AppColors.softInk,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: severityColor(prediction.severity).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          severityLabel(prediction.severity),
                          style: TextStyle(
                            color: severityColor(prediction.severity),
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    prediction.disease,
                    style: const TextStyle(
                      color: AppColors.ink,
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      height: 1.1,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Confidence: $confidencePercent% | Estimated affected area: $lesionPercent%',
                    style: const TextStyle(
                      color: AppColors.softInk,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 18),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      value: prediction.confidence.clamp(0.0, 1.0).toDouble(),
                      minHeight: 10,
                      backgroundColor: const Color(0xFFE7EEE5),
                      valueColor: AlwaysStoppedAnimation<Color>(
                        severityColor(prediction.severity),
                      ),
                    ),
                  ),
                  if (prediction.advisory != null) ...[
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9FBF6),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Farmer message',
                            style: TextStyle(
                              color: AppColors.pine,
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            prediction.advisory!.farmerMessage,
                            style: const TextStyle(
                              color: AppColors.ink,
                              fontSize: 14,
                              height: 1.5,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            prediction.advisory!.nextStep,
                            style: const TextStyle(
                              color: AppColors.softInk,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          _SectionCard(
            title: 'Treatment recommendation',
            subtitle: 'Model 2 output shaped for quick field action.',
            child: Column(
              children: [
                _TreatmentTile(
                  icon: Icons.science_outlined,
                  label: 'Chemical',
                  text: prediction.treatment.chemical,
                ),
                const SizedBox(height: 12),
                _TreatmentTile(
                  icon: Icons.spa_outlined,
                  label: 'Organic',
                  text: prediction.treatment.organic,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _MiniInfoTile(
                        label: 'Dosage',
                        value: prediction.treatment.dosage,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _MiniInfoTile(
                        label: 'Frequency',
                        value: prediction.treatment.frequency,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Prevention steps',
                    style: TextStyle(
                      color: AppColors.ink.withValues(alpha: 0.9),
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                ...prediction.treatment.prevention.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 9,
                          height: 9,
                          margin: const EdgeInsets.only(top: 6),
                          decoration: const BoxDecoration(
                            color: AppColors.pine,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            item,
                            style: const TextStyle(
                              color: AppColors.ink,
                              fontSize: 14,
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          _buildWeatherSection(topRisks),
          if (prediction.topPredictions.isNotEmpty) ...[
            const SizedBox(height: 18),
            _SectionCard(
              title: 'Model confidence spread',
              subtitle: 'Top predictions returned by Model 1.',
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                children: prediction.topPredictions
                    .map(
                      (candidate) => Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF9FBF6),
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(
                          '${candidate.label} • ${(candidate.confidence * 100).toStringAsFixed(0)}%',
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
          const SizedBox(height: 18),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
            child: const Text('Scan Another Leaf'),
          ),
        ],
      ),
    );
  }

  Widget _buildWeatherSection(List<WeatherRiskItem> topRisks) {
    if (_loadingWeather && _weatherRisk == null) {
      return const _SectionCard(
        title: 'Upcoming disease risks',
        subtitle: 'Checking live weather conditions...',
        child: Center(
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: CircularProgressIndicator(color: AppColors.pine),
          ),
        ),
      );
    }

    if (_weatherError != null && _weatherRisk == null) {
      return _SectionCard(
        title: 'Upcoming disease risks',
        subtitle: 'Weather check could not be completed',
        child: Text(
          _weatherError!,
          style: const TextStyle(
            color: AppColors.softInk,
            fontSize: 14,
            height: 1.5,
          ),
        ),
      );
    }

    if (topRisks.isEmpty) {
      return const SizedBox.shrink();
    }

    return _SectionCard(
      title: 'Upcoming disease risks',
      subtitle: _weatherRisk?.location ?? 'Weather-based forecast',
      child: Column(
        children: [
          for (final risk in topRisks) ...[
            _RiskTile(risk: risk),
            if (risk != topRisks.last) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: AppColors.ink,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(
                color: AppColors.softInk,
                fontSize: 13,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}

class _TreatmentTile extends StatelessWidget {
  const _TreatmentTile({
    required this.icon,
    required this.label,
    required this.text,
  });

  final IconData icon;
  final String label;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FBF6),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.pine.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: AppColors.pine),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: AppColors.pine,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  text,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniInfoTile extends StatelessWidget {
  const _MiniInfoTile({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FBF6),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppColors.softInk,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.ink,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class _RiskTile extends StatelessWidget {
  const _RiskTile({required this.risk});

  final WeatherRiskItem risk;

  @override
  Widget build(BuildContext context) {
    final tone = severityColor(risk.riskLevel);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: tone.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  risk.disease,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: tone,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  risk.riskLevel.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            risk.preventionTip,
            style: const TextStyle(
              color: AppColors.ink,
              fontSize: 14,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Confidence ${(risk.confidence * 100).toStringAsFixed(0)}% | urgency ${risk.urgencyDays} day${risk.urgencyDays == 1 ? '' : 's'}',
            style: const TextStyle(
              color: AppColors.softInk,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
