# Extractor de Telefe para Django

Este módulo sólo descubre la URL que usa el reproductor oficial. No descarga
segmentos, no retransmite el video y no intenta evadir DRM, autenticación,
paywalls ni restricciones geográficas.

## Flujo verificado de Telefe

Al cargar `https://www.mitelefe.com/telefe-en-vivo`:

1. Un script inline encuentra `LAMBDA_URL` y `STREAM_ID`.
2. La página ejecuta `GET {LAMBDA_URL}?stream_id={STREAM_ID}`.
3. La respuesta JSON contiene `access_token`, `stream_id` y `player_id`.
4. Se crea el iframe `https://mdstrm.com/live-stream/{stream_id}?player=...&access_token=...`.
5. El HTML del iframe contiene `window.MDSTRM.OPTIONS.src.hls`, actualmente una
   playlist `https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8`.
6. Mediastream valida el contexto de reproducción. Sin `Referer` devuelve
   `REFERRER`; sin la sesión/token obtenida al abrir el iframe puede devolver
   `CLOSED_ACCESS` / `Invalid Token`.

El token no se guarda como constante. Se solicita uno nuevo en cada ejecución.
La página cachea el resultado durante 25 minutos; el extractor usa una
ventana operativa conservadora de 20 minutos y debe ejecutarse nuevamente para
renovar el canal.

## Instalación

Agregá `streaming` a `INSTALLED_APPS` y configurá el app de `Channel`:

```python
INSTALLED_APPS = [
    # ...
    "streaming",
]

CHANNEL_MODEL = "channel.Channel"  # reemplazar por tu app real
```

Dependencia HTTP:

```bash
pip install httpx
```

El fallback opcional requiere:

```bash
pip install playwright
playwright install chromium
```

## Uso

```bash
python manage.py refresh_channel_stream telefe
```

Para diagnosticar sin persistir:

```bash
python manage.py refresh_channel_stream telefe --dry-run
```

Si hay varias variantes importadas de Telefe, el comando prefiere el canal
`Telefe (1080p)` cuando existe; para otros casos conserva la validación de
coincidencias ambiguas.

El servicio se puede usar directamente:

```python
from streaming.extractors.telefe import TelefeStreamExtractor
from streaming.services.channel_stream_service import ChannelStreamService

result = TelefeStreamExtractor().get_stream()
print(result.to_dict())

# Persistencia separada:
ChannelStreamService(TelefeStreamExtractor()).refresh_channel(channel)
```

## Headers y Flutter

El extractor devuelve `Referer`, `Origin` y `User-Agent`. Si el flujo HTTP
obtuvo una cookie necesaria para validar la sesión del iframe, también devuelve
`Cookie`. Flutter debe enviar esos headers con el reproductor HLS; no debe
guardar permanentemente el token ni asumir que la URL sirve indefinidamente.

## El Nueve

El extractor adicional se usa así:

```bash
python manage.py refresh_channel_stream elnueve
```

La página actual de El Nueve carga un iframe de YouTube (`youtube.com/embed`),
por lo que no hay una URL HLS permanente en el HTML. El extractor intenta, en
orden:

1. una URL HLS explícita en el HTML;
2. un canal Twitch detectado en la página, usando `PlaybackAccessToken`;
3. Playwright, interceptando `.m3u8` o respuestas JSON del reproductor oficial.

El antiguo canal Twitch conocido es `elnueveenvivo`, pero no se usa por defecto
porque la página actual publica YouTube. Para probarlo explícitamente:

```bash
python manage.py refresh_channel_stream elnueve --legacy-twitch
```

Ese modo sigue solicitando un token nuevo a `gql.twitch.tv/gql`; no guarda el
token ni hardcodea la playlist firmada.

Si la cookie/token queda ligada al navegador, IP o sesión y la playlist no
puede validarse desde el extractor, el comando falla en vez de guardar una URL
que Flutter no podrá reproducir de forma legítima. En ese caso hay que tratarlo
como una limitación del proveedor, no como un problema para resolver mediante
proxy o evasión.

## Logs

El extractor registra status de landing, Lambda, iframe y manifest, además de
la ruta de descubrimiento y el tipo de playlist. Nunca registra el valor del
`access_token`; las URLs de diagnóstico lo redactan.
