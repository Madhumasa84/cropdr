import 'dart:async';
import 'dart:collection';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/app_models.dart';

class ApiService {
  static const String _configuredBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const String _desktopLoopbackUrl = 'http://127.0.0.1:8000';
  static const String _androidEmulatorUrl = 'http://10.0.2.2:8000';
  static const String _androidLoopbackUrl = 'http://127.0.0.1:8000';

  static String? _lastSuccessfulBaseUrl;

  static String get baseUrl {
    return _candidateBaseUrls.first;
  }

  static String get activeBaseUrl {
    return _lastSuccessfulBaseUrl ?? baseUrl;
  }

  static String? get configurationWarning {
    final url = baseUrl.trim().toLowerCase();
    if (url.contains('your_pc_ip') ||
        url.contains('<your_pc_ip>') ||
        url.contains('your-ip') ||
        url.contains('replace-me')) {
      return 'API_BASE_URL is still using a placeholder. Replace it with your computer IP, for example http://192.168.1.5:8000.';
    }
    if (url.contains('0.0.0.0')) {
      return 'Use a reachable backend address instead of 0.0.0.0. For example use http://127.0.0.1:8000 on desktop/web or your PC LAN IP on a phone.';
    }
    return null;
  }

  static Future<ScanResult> predictImage({
    required XFile imageFile,
    required String crop,
    String? location,
  }) async {
    _validateConfiguration();

    final bytes = await imageFile.readAsBytes();
    return _sendWithFallback<ScanResult>(
      timeoutMessage: 'The image request took too long.',
      send: (resolvedBaseUrl) async {
        final request = http.MultipartRequest(
          'POST',
          Uri.parse('$resolvedBaseUrl/predict/image'),
        );

        request.fields['crop'] = crop;
        if (location != null && location.trim().isNotEmpty) {
          request.fields['location'] = location;
        }

        request.files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: imageFile.name,
          ),
        );

        final streamed = await request.send().timeout(const Duration(seconds: 45));
        final response = await http.Response.fromStream(streamed);
        final payload = _decodeBody(response);

        if (response.statusCode >= 400) {
          throw _ApiResponseException(
            _errorMessage(payload, fallback: 'Image prediction failed.'),
          );
        }
        return ScanResult.fromJson(payload);
      },
    );
  }

  static Future<WeatherRiskResult> getWeatherRisk({
    required String crop,
    String? location,
    double? latitude,
    double? longitude,
  }) async {
    _validateConfiguration();

    final body = <String, dynamic>{'crop': crop};
    if (location != null && location.trim().isNotEmpty) {
      body['location'] = location;
    }
    if (latitude != null) {
      body['latitude'] = latitude;
    }
    if (longitude != null) {
      body['longitude'] = longitude;
    }

    return _sendWithFallback<WeatherRiskResult>(
      timeoutMessage: 'Weather risk check timed out.',
      send: (resolvedBaseUrl) async {
        final response = await http
            .post(
              Uri.parse('$resolvedBaseUrl/predict/weather-risk'),
              headers: const {'Content-Type': 'application/json'},
              body: jsonEncode(body),
            )
            .timeout(const Duration(seconds: 25));

        final payload = _decodeBody(response);
        if (response.statusCode >= 400) {
          throw _ApiResponseException(
            _errorMessage(payload, fallback: 'Weather risk request failed.'),
          );
        }
        return WeatherRiskResult.fromJson(payload);
      },
    );
  }

  static void _validateConfiguration() {
    final warning = configurationWarning;
    if (warning != null) {
      throw Exception(warning);
    }
  }

  static List<String> get _candidateBaseUrls {
    final candidates = <String>[];
    final configured = _sanitizeBaseUrl(_configuredBaseUrl);

    if (configured.isNotEmpty) {
      candidates.add(configured);
    }

    if (kIsWeb || defaultTargetPlatform == TargetPlatform.windows) {
      candidates.add(_desktopLoopbackUrl);
    } else if (defaultTargetPlatform == TargetPlatform.android) {
      if (configured.isNotEmpty) {
        candidates.add(_androidLoopbackUrl);
        candidates.add(_androidEmulatorUrl);
      } else {
        candidates.add(_androidEmulatorUrl);
        candidates.add(_androidLoopbackUrl);
      }
    } else {
      candidates.add(_desktopLoopbackUrl);
    }

    return LinkedHashSet<String>.from(
      candidates
          .map(_sanitizeBaseUrl)
          .where((value) => value.isNotEmpty),
    ).toList();
  }

  static Future<T> _sendWithFallback<T>({
    required String timeoutMessage,
    required Future<T> Function(String resolvedBaseUrl) send,
  }) async {
    final candidates = _candidateBaseUrls;
    Exception? lastTransportError;

    for (var index = 0; index < candidates.length; index++) {
      final resolvedBaseUrl = candidates[index];
      final isLastCandidate = index == candidates.length - 1;

      try {
        final result = await send(resolvedBaseUrl);
        _lastSuccessfulBaseUrl = resolvedBaseUrl;
        return result;
      } on TimeoutException {
        lastTransportError = Exception(
          '$timeoutMessage Check that the backend is running and reachable at $resolvedBaseUrl.',
        );
        if (isLastCandidate) {
          throw lastTransportError;
        }
      } on _ApiResponseException catch (error) {
        throw Exception(error.message);
      } catch (error) {
        final message = _humanizeError(error, baseUrl: resolvedBaseUrl);
        if (!_isRetriableTransportError(message) || isLastCandidate) {
          throw Exception(message);
        }
        lastTransportError = Exception(message);
      }
    }

    throw lastTransportError ??
        Exception('Cannot reach the backend at ${candidates.first}.');
  }

  static Map<String, dynamic> _decodeBody(http.Response response) {
    if (response.body.isEmpty) {
      return <String, dynamic>{};
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return <String, dynamic>{'data': decoded};
  }

  static String _errorMessage(
    Map<String, dynamic> payload, {
    required String fallback,
  }) {
    final detail = payload['detail'];
    if (detail is String && detail.trim().isNotEmpty) {
      return detail;
    }
    final message = payload['message'];
    if (message is String && message.trim().isNotEmpty) {
      return message;
    }
    return fallback;
  }

  static String _sanitizeBaseUrl(String raw) {
    final trimmed = raw.trim();
    if (trimmed.isEmpty) {
      return '';
    }

    final withoutTrailingSlash = trimmed.replaceFirst(RegExp(r'/+$'), '');
    final parsed = Uri.tryParse(withoutTrailingSlash);
    if (parsed == null || parsed.host.isEmpty) {
      return withoutTrailingSlash;
    }

    final isLocalTarget = parsed.host == 'localhost' ||
        parsed.host == '127.0.0.1' ||
        parsed.host == '10.0.2.2' ||
        _isPrivateIpv4(parsed.host);

    if (parsed.scheme == 'https' && isLocalTarget) {
      return parsed.replace(scheme: 'http').toString();
    }

    return withoutTrailingSlash;
  }

  static bool _isPrivateIpv4(String host) {
    final match = RegExp(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
        .firstMatch(host);
    if (match == null) {
      return false;
    }

    final octets = List<int>.generate(
      4,
      (index) => int.tryParse(match.group(index + 1) ?? '') ?? -1,
    );
    if (octets.any((value) => value < 0 || value > 255)) {
      return false;
    }

    return octets[0] == 10 ||
        (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31) ||
        (octets[0] == 192 && octets[1] == 168);
  }

  static bool _isRetriableTransportError(String message) {
    final lowered = message.toLowerCase();
    return lowered.contains('cannot reach the backend') ||
        lowered.contains('connection was refused') ||
        lowered.contains('network is unreachable') ||
        lowered.contains('timed out') ||
        lowered.contains('secure connection');
  }

  static String _humanizeError(
    Object error, {
    required String baseUrl,
  }) {
    final raw = error.toString().replaceFirst('Exception: ', '').trim();
    final lowered = raw.toLowerCase();

    if (lowered.contains('handshakeexception') ||
        lowered.contains('certificate') ||
        lowered.contains('wrong version number')) {
      return 'Cannot establish a secure connection to $baseUrl. The local backend only serves HTTP, so use http:// instead of https://.';
    }
    if (lowered.contains('clientfailed to fetch') ||
        lowered.contains('failed to fetch') ||
        lowered.contains('xmlhttprequest error')) {
      return 'Cannot reach the backend at $baseUrl. Start the FastAPI server and make sure API_BASE_URL points to the correct machine.';
    }
    if (lowered.contains('connection refused')) {
      return 'Connection was refused by $baseUrl. Start the backend server and try again.';
    }
    if (lowered.contains('network is unreachable')) {
      return 'Network is unreachable. Verify the phone/emulator can reach $baseUrl.';
    }
    return raw;
  }
}

class _ApiResponseException implements Exception {
  const _ApiResponseException(this.message);

  final String message;
}
