import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:workout_app/widgets/custom_bottom_nav_bar.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';

void main() {
  testWidgets('bottom navigation grows for larger system text', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    Widget app(double scale) => MaterialApp(
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: TextScaler.linear(scale),
        ),
        child: child!,
      ),
      home: Scaffold(
        bottomNavigationBar: CustomBottomNavBar(
          currentIndex: 0,
          onTap: (_) {},
          items: const [
            BottomNavBarItem(icon: Icons.fitness_center, label: 'Тренировки'),
            BottomNavBarItem(icon: Icons.schedule, label: 'Планы тренировок'),
            BottomNavBarItem(icon: Icons.people, label: 'Сообщество'),
            BottomNavBarItem(icon: Icons.business, label: 'Клиенты'),
            BottomNavBarItem(icon: Icons.bug_report, label: 'Отладка'),
          ],
        ),
      ),
    );

    await tester.pumpWidget(app(1));
    final normalHeight = tester.getSize(find.byType(CustomBottomNavBar)).height;
    await tester.pumpWidget(app(2));
    await tester.pumpAndSettle();
    final largeTextHeight = tester.getSize(find.byType(CustomBottomNavBar)).height;

    expect(largeTextHeight, greaterThan(normalHeight));
    expect(tester.takeException(), isNull);
  });

  testWidgets('app bar keeps title clear of actions on a narrow screen', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        appBar: PrimaryAppBar.detail(
          title: 'Очень длинное название экрана тренировок',
          actions: [
            IconButton(onPressed: () {}, icon: const Icon(Icons.search)),
            IconButton(onPressed: () {}, icon: const Icon(Icons.more_vert)),
          ],
        ),
      ),
    ));

    final title = tester.getRect(find.text('Очень длинное название экрана тренировок'));
    final search = tester.getRect(find.byIcon(Icons.search));
    expect(title.right, lessThanOrEqualTo(search.left));
    expect(tester.takeException(), isNull);
  });
}
