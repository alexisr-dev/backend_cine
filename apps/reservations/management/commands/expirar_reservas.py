import time

from django.core.management.base import BaseCommand

from apps.reservations.tasks import barrer_reservas_expiradas


class Command(BaseCommand):
    help = "Libera los asientos con hold vencido y marca las reservas como expiradas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--intervalo",
            type=int,
            default=0,
            help="Segundos entre barridos. 0 ejecuta una sola vez.",
        )

    def handle(self, *args, **options):
        intervalo = options["intervalo"]
        while True:
            liberados = barrer_reservas_expiradas()
            self.stdout.write(self.style.SUCCESS(f"Asientos liberados: {liberados}"))
            if intervalo <= 0:
                break
            time.sleep(intervalo)
