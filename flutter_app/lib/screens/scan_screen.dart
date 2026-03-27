import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/app_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'result_screen.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({
    super.key,
    required this.crop,
    this.initialWeatherRisk,
    this.locationLabel,
    this.latitude,
    this.longitude,
  });

  final String crop;
  final WeatherRiskResult? initialWeatherRisk;
  final String? locationLabel;
  final double? latitude;
  final double? longitude;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final ImagePicker _picker = ImagePicker();
  XFile? _selectedImage;
  Uint8List? _selectedBytes;
  bool _isAnalyzing = false;

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(
      source: source,
      imageQuality: 88,
      maxWidth: 1600,
    );

    if (picked == null) {
      return;
    }

    final bytes = await picked.readAsBytes();
    if (!mounted) {
      return;
    }

    setState(() {
      _selectedImage = picked;
      _selectedBytes = bytes;
    });
  }

  Future<void> _analyseLeaf() async {
    if (_selectedImage == null || _selectedBytes == null || _isAnalyzing) {
      return;
    }

    setState(() {
      _isAnalyzing = true;
    });

    try {
      final prediction = await ApiService.predictImage(
        imageFile: _selectedImage!,
        crop: widget.crop,
        location: widget.locationLabel,
      );

      if (!mounted) {
        return;
      }

      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => ResultScreen(
            imageBytes: _selectedBytes!,
            prediction: prediction,
            weatherRisk: widget.initialWeatherRisk,
            locationLabel: widget.locationLabel,
            latitude: widget.latitude,
            longitude: widget.longitude,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isAnalyzing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Leaf'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: AppColors.pine.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Icon(
                      Icons.eco_outlined,
                      color: AppColors.pine,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.crop,
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          widget.locationLabel ?? 'Current field location',
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
              ),
            ),
          ),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Take a clear photo of the affected leaf',
                    style: TextStyle(
                      color: AppColors.ink,
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Fill most of the frame with one leaf. Avoid strong shadows when possible.',
                    style: TextStyle(
                      color: AppColors.softInk,
                      fontSize: 14,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 18),
                  GestureDetector(
                    onTap: () => _pickImage(ImageSource.gallery),
                    child: Container(
                      height: 300,
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9FBF6),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: _selectedBytes == null ? AppColors.border : AppColors.pine,
                          width: _selectedBytes == null ? 1.4 : 2,
                        ),
                      ),
                      child: _selectedBytes == null
                          ? const Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.add_photo_alternate_outlined,
                                  size: 60,
                                  color: AppColors.leaf,
                                ),
                                SizedBox(height: 16),
                                Text(
                                  'Tap to choose from gallery',
                                  style: TextStyle(
                                    color: AppColors.softInk,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            )
                          : ClipRRect(
                              borderRadius: BorderRadius.circular(22),
                              child: Image.memory(
                                _selectedBytes!,
                                fit: BoxFit.cover,
                                width: double.infinity,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _pickImage(ImageSource.gallery),
                          icon: const Icon(Icons.photo_library_outlined),
                          label: const Text('Gallery'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _pickImage(ImageSource.camera),
                          icon: const Icon(Icons.camera_alt_outlined),
                          label: const Text('Camera'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          ElevatedButton(
            onPressed: _selectedImage == null || _isAnalyzing ? null : _analyseLeaf,
            child: _isAnalyzing
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.4,
                      color: Colors.white,
                    ),
                  )
                : const Text('Analyse Leaf'),
          ),
        ],
      ),
    );
  }
}
