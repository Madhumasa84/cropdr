import 'package:crop_disease_platform_app/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('home screen renders crop doctor shell', (WidgetTester tester) async {
    await tester.pumpWidget(const CropDoctorApp());
    await tester.pump();

    expect(find.text('Crop Doctor'), findsOneWidget);
    expect(find.text('Select crop'), findsOneWidget);
    expect(find.text('Scan Leaf'), findsOneWidget);
  });
}
