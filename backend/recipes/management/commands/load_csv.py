import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Автоматический импортёр CSV'

    def handle(self, *args, **kwargs):
        data_dir = Path(settings.BASE_DIR).parent / 'data'

        models_files = {
            Ingredient: 'ingredients.csv',
        }

        field_names = {
            Ingredient: ('name', 'measurement_unit'),
        }

        for model, filename in models_files.items():
            self.stdout.write(f'Началась загрузка файла: "{filename}".')

            file_path = data_dir / filename

            with open(file_path, encoding='utf-8') as f:
                reader = csv.DictReader(f, fieldnames=field_names[model])
                objects = [model(**row) for row in reader]
                model.objects.bulk_create(objects, ignore_conflicts=True)

            self.stdout.write(f'Завершилась загрузка файла: "{filename}".')
        self.stdout.write(self.style.SUCCESS('Данные успешно загружены!'))
