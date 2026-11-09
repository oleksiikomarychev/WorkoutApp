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

  testWidgets('main app bar centers its agent title with one action', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        appBar: PrimaryAppBar.main(
          title: 'Workouts',
          actions: [IconButton(onPressed: () {}, icon: const Icon(Icons.person))],
        ),
      ),
    ));

    final titleCenter = tester.getCenter(find.text('Workouts')).dx;
    expect(titleCenter, closeTo(160, 4));
    expect(tester.takeException(), isNull);
  });

  testWidgets('dark app bar keeps the assistant action discoverable', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var taps = 0;

    await tester.pumpWidget(MaterialApp(
      theme: ThemeData.dark(),
      home: Scaffold(
        appBar: PrimaryAppBar.main(
          title: 'Workouts',
          onTitleTap: () => taps++,
          actions: [IconButton(onPressed: () {}, icon: const Icon(Icons.person))],
        ),
      ),
    ));

    expect(find.byIcon(Icons.auto_awesome_outlined), findsOneWidget);
    await tester.tap(find.text('Workouts'));
    expect(taps, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('plan title stays centered between back and two actions', (tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 700));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(MaterialApp(
      theme: ThemeData.dark(),
      home: Scaffold(
        appBar: PrimaryAppBar(
          title: 'Training Plans',
          showBack: true,
          actions: [
            IconButton(onPressed: () {}, icon: const Icon(Icons.check)),
            IconButton(onPressed: () {}, icon: const Icon(Icons.more_vert)),
          ],
        ),
      ),
    ));

    expect(tester.getCenter(find.text('Training Plans')).dx, closeTo(200, 4));
    expect(tester.takeException(), isNull);
  });
}
