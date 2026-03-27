import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../models/app_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'scan_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const List<String> _crops = <String>[
    'Tomato',
    'Rice',
    'Wheat',
    'Cotton',
    'Maize',
    'Groundnut',
    'Potato',
    'Chilli',
    'Sugarcane',
    'Soybean',
  ];

  String _selectedCrop = 'Tomato';
  WeatherRiskResult? _weatherRisk;
  bool _loadingRisk = false;
  bool _usingFallbackLocation = false;
  String? _riskError;
  double? _latitude;
  double? _longitude;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refreshWeatherRisk();
    });
  }

  Future<void> _refreshWeatherRisk() async {
    if (_loadingRisk) {
      return;
    }

    setState(() {
      _loadingRisk = true;
      _riskError = null;
    });

    try {
      final resolvedLocation = await _resolveLocation();
      final response = await ApiService.getWeatherRisk(
        crop: _selectedCrop,
        location: resolvedLocation.location,
        latitude: resolvedLocation.latitude,
        longitude: resolvedLocation.longitude,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _weatherRisk = response;
        _latitude = response.coordinates?.latitude ?? resolvedLocation.latitude;
        _longitude = response.coordinates?.longitude ?? resolvedLocation.longitude;
        _usingFallbackLocation = resolvedLocation.isFallback;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _riskError = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _loadingRisk = false;
        });
      }
    }
  }

  Future<_ResolvedLocation> _resolveLocation() async {
    const fallbackLocation = 'Chennai, Tamil Nadu';

    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return const _ResolvedLocation(location: fallbackLocation, isFallback: true);
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return const _ResolvedLocation(location: fallbackLocation, isFallback: true);
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
        ),
      );

      return _ResolvedLocation(
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (_) {
      return const _ResolvedLocation(location: fallbackLocation, isFallback: true);
    }
  }

  Future<void> _openScanScreen() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ScanScreen(
          crop: _selectedCrop,
          initialWeatherRisk: _weatherRisk,
          locationLabel: _weatherRisk?.location,
          latitude: _latitude,
          longitude: _longitude,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final topRisk = _weatherRisk?.risks.isNotEmpty == true ? _weatherRisk!.risks.first : null;
    final weatherSummary = _weatherRisk?.weatherSummary;
    final currentSnapshot = _weatherRisk?.currentSnapshot;
    final configWarning = ApiService.configurationWarning;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Crop Doctor'),
      ),
      body: RefreshIndicator(
        color: AppColors.pine,
        onRefresh: _refreshWeatherRisk,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(28),
                gradient: const LinearGradient(
                  colors: <Color>[AppColors.pine, Color(0xFF3B6E46), AppColors.moss],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '3 models working together',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Catch disease early,\nact before it spreads.',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 27,
                      fontWeight: FontWeight.w800,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    topRisk == null
                        ? 'Scan a leaf for diagnosis and treatment, or check weather-driven disease risk for your crop.'
                        : 'Current top weather alert for $_selectedCrop: ${topRisk.disease} (${severityLabel(topRisk.riskLevel)}).',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 15,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _openScanScreen,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppColors.pine,
                          ),
                          icon: const Icon(Icons.camera_alt_outlined),
                          label: const Text('Scan Leaf'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 22),
            if (configWarning != null) ...[
              _SectionCard(
                title: 'Backend setup needed',
                subtitle: ApiService.baseUrl,
                child: Text(
                  configWarning,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ),
              const SizedBox(height: 18),
            ],
            _SectionCard(
              title: 'Select crop',
              subtitle: 'Choose the crop before checking risk or analysing a leaf image.',
              child: DropdownButtonFormField<String>(
                initialValue: _selectedCrop,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.agriculture_outlined),
                ),
                borderRadius: BorderRadius.circular(18),
                items: _crops
                    .map(
                      (crop) => DropdownMenuItem<String>(
                        value: crop,
                        child: Text(crop),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value == null || value == _selectedCrop) {
                    return;
                  }
                  setState(() {
                    _selectedCrop = value;
                  });
                  _refreshWeatherRisk();
                },
              ),
            ),
            const SizedBox(height: 18),
            _SectionCard(
              title: 'Weather-based risk',
              subtitle: _weatherRisk?.location ?? ApiService.baseUrl,
              trailing: OutlinedButton.icon(
                onPressed: _loadingRisk ? null : _refreshWeatherRisk,
                icon: _loadingRisk
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.cloud_sync_outlined),
                label: Text(_loadingRisk ? 'Checking' : 'Check Risk'),
              ),
              child: _buildWeatherContent(
                weatherSummary: weatherSummary,
                currentSnapshot: currentSnapshot,
                topRisk: topRisk,
              ),
            ),
            if (_usingFallbackLocation) ...[
              const SizedBox(height: 12),
              const Text(
                'Using demo fallback location because device location is unavailable.',
                style: TextStyle(
                  color: AppColors.softInk,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
            if (_weatherRisk != null) ...[
              const SizedBox(height: 18),
              const _SectionCard(
                title: 'What the app will do',
                subtitle: 'End-to-end backend flow for the farmer experience.',
                child: Column(
                  children: [
                    _FlowTile(
                      icon: Icons.photo_camera_front_outlined,
                      title: 'Model 1',
                      description: 'Detects crop disease, confidence, and severity from the leaf image.',
                    ),
                    SizedBox(height: 10),
                    _FlowTile(
                      icon: Icons.medication_outlined,
                      title: 'Model 2',
                      description: 'Returns chemical treatment, organic option, dosage, and prevention steps.',
                    ),
                    SizedBox(height: 10),
                    _FlowTile(
                      icon: Icons.thunderstorm_outlined,
                      title: 'Model 3',
                      description: 'Predicts upcoming disease risk from weather and crop context.',
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildWeatherContent({
    required WeatherSummary? weatherSummary,
    required WeatherSnapshot? currentSnapshot,
    required WeatherRiskItem? topRisk,
  }) {
    if (_riskError != null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: const Color(0xFFFFF4F1),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: AppColors.danger),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _riskError!,
                style: const TextStyle(
                  color: AppColors.ink,
                  fontSize: 14,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_loadingRisk && _weatherRisk == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 10),
        child: Center(
          child: CircularProgressIndicator(color: AppColors.pine),
        ),
      );
    }

    if (_weatherRisk == null || weatherSummary == null) {
      return const Text(
        'Weather risk will appear here after the first successful check.',
        style: TextStyle(color: AppColors.softInk, fontSize: 14),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _MetricCard(
              label: 'Temperature',
              value: '${weatherSummary.tempAvg.toStringAsFixed(1)} deg C',
              icon: Icons.thermostat_outlined,
            ),
            _MetricCard(
              label: 'Humidity',
              value: '${weatherSummary.humidityAvg.toStringAsFixed(0)}%',
              icon: Icons.water_drop_outlined,
            ),
            _MetricCard(
              label: '7 day rain',
              value: '${weatherSummary.rainfall7dayMm.toStringAsFixed(1)} mm',
              icon: Icons.grain_outlined,
            ),
          ],
        ),
        if (currentSnapshot != null) ...[
          const SizedBox(height: 16),
          Text(
            'Now: ${currentSnapshot.description.isEmpty ? 'Weather data available' : currentSnapshot.description}',
            style: const TextStyle(
              color: AppColors.softInk,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
        if (topRisk != null) ...[
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: severityColor(topRisk.riskLevel).withValues(alpha: 0.10),
              border: Border.all(
                color: severityColor(topRisk.riskLevel).withValues(alpha: 0.20),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: severityColor(topRisk.riskLevel),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        severityLabel(topRisk.riskLevel),
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      '${(topRisk.confidence * 100).toStringAsFixed(0)}% confidence',
                      style: const TextStyle(
                        color: AppColors.softInk,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  topRisk.disease,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  topRisk.preventionTip,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Act within ${topRisk.urgencyDays} day${topRisk.urgencyDays == 1 ? '' : 's'} if conditions stay the same.',
                  style: const TextStyle(
                    color: AppColors.softInk,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _ResolvedLocation {
  const _ResolvedLocation({
    this.location,
    this.latitude,
    this.longitude,
    this.isFallback = false,
  });

  final String? location;
  final double? latitude;
  final double? longitude;
  final bool isFallback;
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
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
                    ],
                  ),
                ),
                if (trailing != null) ...[
                  const SizedBox(width: 12),
                  trailing!,
                ],
              ],
            ),
            const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 140),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FBF6),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.pine),
          const SizedBox(height: 12),
          Text(
            label,
            style: const TextStyle(
              color: AppColors.softInk,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.ink,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _FlowTile extends StatelessWidget {
  const _FlowTile({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

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
        children: [
          Container(
            width: 46,
            height: 46,
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
                  title,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(
                    color: AppColors.softInk,
                    fontSize: 13,
                    height: 1.4,
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
