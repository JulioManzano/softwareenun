import requests
from django.db import transaction

from channel.models import Channel


def import_m3u(url):
    response = requests.get(url, timeout=10)
    lines = response.text.splitlines()

    country_code = url.split("/")[-1].replace(".m3u", "").upper()

    existing_channels = set()
    name = ""
    logo = ""
    category = ""

    with transaction.atomic():

        for line in lines:

            if line.startswith("#EXTINF"):

                name = line.split(",")[-1].strip()[:255]

                logo = ""
                category = "General"

                if 'tvg-logo="' in line:
                    logo = line.split('tvg-logo="')[1].split('"')[0][:1000]

                if 'group-title="' in line:
                    category = line.split('group-title="')[1].split('"')[0][:255]

            elif line.startswith("http"):

                stream_url = line.strip()[:1000]

                channel, created = Channel.objects.update_or_create(
                    name=name,
                    country=country_code,
                    defaults={
                        "logo": logo,
                        "url": stream_url,
                        "category": category,
                        "use_hls": stream_url.endswith(".m3u8"),
                        "link_direct": True,
                        "is_active": True,
                        "source" : "IPTV/ORG"
                    }
                )

                existing_channels.add(channel.id)

        # 🔥 Desactivar los que ya no existen
        Channel.objects.filter(
            country=country_code,
            source = "IPTV/ORG"
        ).exclude(
            id__in=existing_channels
        ).update(is_active=False)