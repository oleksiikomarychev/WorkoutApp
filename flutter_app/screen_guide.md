# Screen Design Guide

Цей документ описує основні UI-концепти, які використовуються в проєкті. Дотримуйтесь цих правил при створенні нових екранів, щоб зберігати єдиний стиль застосунку.

---

## 1. Каркас екрана (Scaffold + AssistantChatHost)

Будь-який «прикладний» екран має бути обгорнутий у `AssistantChatHost`. Це додає глобальний overlay AI-асистента та віддає колбек `openChat`, який далі використовується в `PrimaryAppBar` (тап по тайтлу відкриває чат).

### Стандартний шаблон

```dart /dev/null/template.dart#L1-40
@override
Widget build(BuildContext context) {
  return AssistantChatHost(
    // ОПЦІОНАЛЬНО: Передача контексту для AI (наприклад, на екранах деталей)
    contextBuilder: () async => {
      'screen': 'workout_list',
      'entities': {'progression_id': widget.progressionId},
    },
    builder: (context, openChat) {
      return Scaffold(
        appBar: PrimaryAppBar(
          title: 'Заголовок екрана',
          onTitleTap: openChat,
          actions: const [
            // Іконки-дії (без обгорток - PrimaryAppBar сам обертає у glass chip)
            SizedBox(width: 8),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.symmetric(vertical: 12),
            children: [
              // Контент екрана
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: _onAdd,
          child: const Icon(Icons.add),
        ),
      );
    },
  );
}
```

### Правила
- **Завжди** використовувати `PrimaryAppBar` замість стандартного `AppBar`.
- На «головних» екранах розділу — `PrimaryAppBar(...)` з `onTitleTap: openChat`.
- На вкладених/деталізованих екранах — `PrimaryAppBar.detail(title: ...)` (автоматично додає кнопку «назад»).
- Не обгортати `actions` у власні контейнери — `PrimaryAppBar` сам додає glass-chip стиль.
- **AI Context**: Для екранів із специфічними даними (аналітика, деталі плану) обов'язково реалізуйте `contextBuilder`, щоб AI-асистент розумів, на що дивиться користувач.

---

## 2. Кольорова й типографічна системи

У білді отримуйте `colorScheme` та `textTheme` через `Theme.of(context)`:

```dart /dev/null/template.dart#L1-3
final colorScheme = Theme.of(context).colorScheme;
final textTheme = Theme.of(context).textTheme;
```

Для констант використовуйте `lib/config/constants/theme_constants.dart`:
- **Кольори**: `AppColors.primary`, `AppColors.error`
- **Типографіка**: `AppTextStyles.titleLarge`
- **Відступи**: `AppSpacing.md` (16.0)
- **Радіуси**: `AppBorderRadius.lg` (16.0)

> ⚠️ Не використовуйте `Colors.red`, `Colors.grey` напряму — беріть із теми (`colorScheme.error`, `colorScheme.onSurfaceVariant`), інакше зламається dark mode.

---

## 3. Стани екрана (Loading, Error, Empty, Data)

Кожен екран зі завантаженням даних має чітко відображати стани:

- **Loading**: `const LoadingIndicator();`
- **Error**: 
  ```dart /dev/null/template.dart#L1-5
  ErrorState(
    message: 'Не вдалось завантажити дані: $error',
    onRetry: _load,
  );
  ```
- **Empty**:
  ```dart /dev/null/template.dart#L1-5
  const EmptyState(
    icon: Icons.fitness_center,
    title: 'Немає даних',
    description: 'Створіть перший запис',
  );
  ```

---

## 4. Списки, Картки та Складні Скроли

### 4.1 Прості списки
- Зовнішній скрол — `ListView` з `padding: EdgeInsets.symmetric(vertical: 12)`.
- «Вкладені» списки — `ListView.builder` з `shrinkWrap: true` та `physics: NeverScrollableScrollPhysics()`.

### 4.2 Складні скроли (Slivers)
Якщо екран має складну шапку (яка має ховатися) або комбінацію сіток (`GridView`) та списків, використовуйте `CustomScrollView`:

```dart /dev/null/template.dart#L1-10
CustomScrollView(
  slivers: [
    SliverToBoxAdapter(child: HeroCard()),
    SliverPadding(
      padding: const EdgeInsets.all(12),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(...),
      ),
    ),
  ],
)
```

### 4.3 Рядок списку
```dart /dev/null/template.dart#L1-6
ListTile(
  title: Text(item.name),
  subtitle: Text('Опис', style: TextStyle(color: colorScheme.onSurfaceVariant)),
  trailing: const Icon(Icons.chevron_right),
  onTap: _open,
);
```

---

## 5. Діалоги та Повноекранні Форми

### 5.1 Прості форми (Діалоги)
Для швидкого створення (1-2 поля) використовуйте `showDialog` + `AlertDialog` + `StatefulBuilder`.

### 5.2 Складні форми (Повноекранні)
Для сутностей з багатьма полями (наприклад, редактор плану) створюйте окремий екран із використанням `Form`:

```dart /dev/null/template.dart#L1-18
final _formKey = GlobalKey<FormState>();

Form(
  key: _formKey,
  child: Column(
    children: [
      TextFormField(
        controller: _nameController,
        decoration: const InputDecoration(labelText: 'Назва', border: OutlineInputBorder()),
        validator: (value) => value?.isEmpty == true ? 'Обовʼязкове поле' : null,
      ),
      ElevatedButton(
        onPressed: () {
          if (_formKey.currentState!.validate()) {
            _save();
          }
        },
        child: const Text('Зберегти'),
      )
    ],
  ),
)
```
*Правило:* Завжди додавайте `FocusScope.of(context).unfocus();` при збереженні, щоб сховати клавіатуру.

---

## 6. State Management та Завантаження даних (Riverpod)

Нові екрани в проєкті використовують **Riverpod** (замість старого `Provider`). 

```dart /dev/null/template.dart#L1-20
class MyScreen extends ConsumerStatefulWidget {
  const MyScreen({super.key});
  @override
  ConsumerState<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends ConsumerState<MyScreen> {
  bool _isLoading = false;

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      // Використовуємо ref.read для доступу до сервісів
      final service = ref.read(myServiceProvider);
      final data = await service.getData();
      // ...
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }
}
```

*Правила:*
- Наслідуйтесь від `ConsumerStatefulWidget` або `ConsumerWidget`.
- Сервіси отримуйте через `ref.read(providerName)` у методах або `ref.watch(providerName)` у `build`.
- Завжди перевіряйте `if (mounted)` після `await`.

---

## 7. Навігація та Таби

- **Перехід на деталь**: `await Navigator.push<bool>(...)`. Якщо повертається `true`, викликаємо `_refresh()`.
- **Повернення результату**: `Navigator.pop(context, true)`.
- **Кореневі екрани з Bottom Navigation**: Не повинні мати кнопки «Назад» у `PrimaryAppBar` (використовуйте `.main`).

---

## 8. Сповіщення користувача

- Успіх/Помилка: `ScaffoldMessenger.of(context).showSnackBar(...)`.
- Деструктивні дії (видалення): обов'язкове підтвердження через `showDialog` з двома кнопками.

---

## 9. Чек-лист нового екрана

1. [ ] Огорнутий у `AssistantChatHost`? (Чи передано `contextBuilder` для складних екранів?)
2. [ ] Використовує `PrimaryAppBar` (а не стандартний `AppBar`)?
3. [ ] Тіло підтримує скрол (напр. `ListView` або `CustomScrollView`)?
4. [ ] Реалізовано 4 стани: loading / error / empty / data?
5. [ ] Використовуються `Theme.of(context)` та `AppColors`/`AppSpacing`, а не хардкод кольорів?
6. [ ] Використовується **Riverpod** (`ConsumerStatefulWidget`, `ref.read`) для нових екранів?
7. [ ] Перед `setState`/`Navigator` після `await` є перевірка `mounted`?
8. [ ] Контролери (`TextEditingController`) диспозяться у `dispose()`?
9. [ ] Повноекранні форми використовують `Form` та `TextFormField` з валідацією?
10. [ ] Деталь-екрани повертають `true` при змінах, щоб батьківський список оновився?
