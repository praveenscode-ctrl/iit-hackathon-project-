import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:assignhub/main.dart';

void main() {
  testWidgets('Smoke test for AssignHubApp', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AssignHubApp()));
    expect(find.byType(AssignHubApp), findsOneWidget);
  });
}
