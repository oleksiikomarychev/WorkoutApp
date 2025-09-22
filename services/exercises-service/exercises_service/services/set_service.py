class SetService:
    @staticmethod
    def normalize_sets(sets: list) -> list:
        # Нормализует сеты для внутренней обработки.
        normalized = []
        for s in sets:
            if 'reps' not in s:
                raise ValueError("Reps are required for each set")
            ns = s.copy()
            ns['reps'] = int(ns['reps'])
            normalized.append(ns)
        return normalized

    @staticmethod
    def normalize_sets_for_frontend(sets: list) -> list:
        # Нормализует сеты для представления на фронтенде.
        normalized = []
        for s in sets:
            ns = s.copy()
            normalized.append(ns)
        return normalized

    @staticmethod
    def ensure_set_ids(sets: list) -> list:
        # Гарантирует наличие уникальных ID для каждого сета.
        # Генерирует положительные временные ID вместо отрицательных
        max_id = 0
        for s in sets:
            if 'id' in s and s['id'] is not None and isinstance(s['id'], int) and s['id'] > max_id:
                max_id = s['id']
        
        next_temp_id = max_id + 1
        for s in sets:
            if 'id' not in s or s['id'] is None or not isinstance(s['id'], int) or s['id'] <= 0:
                s['id'] = next_temp_id
                next_temp_id += 1
        return sets

    @staticmethod
    def update_set(existing_sets: list, set_id: int, update_data: dict) -> list:
        # Обновляет конкретный сет в списке сетов.
        new_sets = []
        updated = False
        for s in existing_sets:
            if s.get('id') == set_id:
                updated_set = {**s, **update_data}
                new_sets.append(updated_set)
                updated = True
            else:
                new_sets.append(s)
        if not updated:
            raise ValueError(f"Set with id {set_id} not found")
        return new_sets

    def prepare_sets(self, sets_data: list) -> list:
        # Подготавливает сеты для сохранения:
        # 1. Нормализует данные
        # 2. Гарантирует наличие ID
        normalized = self.normalize_sets(sets_data)
        return self.ensure_set_ids(normalized)