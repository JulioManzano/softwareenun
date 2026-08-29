from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
from channel.models import CategoryMovie, Movie
import re

BASE_URL = "https://www.freetv.com"
LIST_URL = "https://www.freetv.com/?section=moviessectionespanol"


def duration_to_minutes(duration_str):
    parts = duration_str.strip().split(":")
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 60 + minutes
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes
    return None


class Command(BaseCommand):
    help = "Import movies from FreeTV"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Iniciando importación FreeTV..."))

        movies_data = []

        # ===============================
        # 🔵 SCRAPING
        # ===============================
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(LIST_URL, timeout=60000)
            page.wait_for_timeout(5000)

            items = page.query_selector_all("a.ottera--row--item")

            self.stdout.write(f"Películas encontradas: {len(items)}")

            movies_links = []

            # 1️⃣ Extraer links primero
            for item in items[:10]:  # limit para pruebas
                external_id = item.get_attribute("data-ottera-id")
                title = item.get_attribute("title")
                relative_url = item.get_attribute("href")

                img = item.query_selector("img")
                poster = img.get_attribute("src") if img else ""

                detail_url = f"{BASE_URL}{relative_url}"

                movies_links.append({
                    "external_id": external_id,
                    "title": title,
                    "poster": poster,
                    "detail_url": detail_url,
                })

                       
            for movie_basic in movies_links:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nProcesando: {movie_basic['title']}"
                    )
                )
                page.goto(movie_basic["detail_url"], timeout=60000)
                page.wait_for_timeout(5000)              
                # Meta info
                meta = page.query_selector(".video--meta--grouped")
                duration = None
                year = None

                if meta:
                    meta_text = meta.inner_text().strip()
                    parts = [p.strip() for p in meta_text.split("/")]

                    if len(parts) >= 3:
                        duration = duration_to_minutes(parts[0])
                        year = int(parts[2]) if parts[2].isdigit() else None

                # Descripción
                desc_element = page.query_selector(
                    ".field--name-field-long-description"
                )
                description = (
                    desc_element.inner_text().strip()
                    if desc_element else ""
                )

                # Géneros
                genres_elements = page.query_selector_all(
                    ".field--name-field-categories .field__item"
                )
                genres = [g.inner_text().strip() for g in genres_elements]

                # Backdrop
                backdrop_element = page.query_selector(
                    ".video--preview--image img"
                )
                backdrop = (
                    backdrop_element.get_attribute("src")
                    if backdrop_element else ""
                )

                # Debug prints
                self.stdout.write(f"ID: {movie_basic['external_id']}")
                self.stdout.write(f"Año: {year}")
                self.stdout.write(f"Duración: {duration}")
                self.stdout.write(f"Géneros: {genres}")
                self.stdout.write("-" * 40)

                movies_data.append({
                    "external_id": movie_basic["external_id"],
                    "title": movie_basic["title"],
                    "description": description,
                    "year": year,
                    "duration": duration,
                    "poster": movie_basic["poster"],
                    "backdrop": backdrop,
                    "source_url": movie_basic["detail_url"],
                    "genres": genres,
                })

            browser.close()

        # ===============================
        # 🟣 GUARDADO EN DB
        # ===============================
        self.stdout.write(self.style.SUCCESS("\nGuardando en base de datos..."))

        for data in movies_data:
            movie, created = Movie.objects.update_or_create(
                external_id=data["external_id"],
                defaults={
                    "title": data["title"],
                    "description": data["description"],
                    "year": data["year"],
                    "duration": data["duration"],
                    "poster": data["poster"],
                    "backdrop": data["backdrop"],
                    "source_url": data["source_url"],
                    "is_active": True,
                }
            )
            
            for genre_name in data["genres"]:
                category, _ = CategoryMovie.objects.get_or_create(
                    name=genre_name
                )
                movie.categories.add(category)

            status = "Creada" if created else "Actualizada"
            self.stdout.write(f"{status}: {data['title']}")

        self.stdout.write(self.style.SUCCESS("\nFinalizado correctamente."))
