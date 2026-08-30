import logging

import replicate
from django.conf import settings


logger = logging.getLogger(__name__)


class ReplicateService:

    @staticmethod
    def enhance_image(
        image_file,
        scale=2,
        face_enhance=False,
    ):
        logger.info(
            "=== REPLICATE ENHANCE IMAGE ==="
        )

        logger.info(
            "Image: %s",
            getattr(image_file, "name", None),
        )

        logger.info(
            "Size: %s bytes",
            getattr(image_file, "size", None),
        )

        logger.info(
            "Scale: %s",
            scale,
        )

        logger.info(
            "Face enhance: %s",
            face_enhance,
        )

        token = settings.REPLICATE_API_TOKEN

        if not token:
            raise Exception(
                "REPLICATE_API_TOKEN no configurado"
            )

        client = replicate.Client(
            api_token=token,
        )

        try:
            logger.info(
                "Preparando archivo para Replicate..."
            )

            # Volvemos al comienzo del archivo.
            image_file.seek(0)

            # Replicate necesita un archivo/stream,
            # no el InMemoryUploadedFile de Django
            # como objeto JSON.
            output = client.run(
                "nightmareai/real-esrgan",
                input={
                    "image": image_file.file,
                    "scale": scale,
                    "face_enhance": face_enhance,
                },
            )

            logger.info(
                "Replicate respondió correctamente."
            )

            logger.info(
                "Output type: %s",
                type(output),
            )

            logger.info(
                "Output: %s",
                output,
            )

            if output is None:
                raise Exception(
                    "Replicate devolvió un output vacío"
                )

            if hasattr(output, "url"):
                url = output.url

            elif isinstance(output, str):
                url = output

            else:
                raise Exception(
                    "Formato de output desconocido: "
                    f"{type(output)}"
                )

            logger.info(
                "Enhanced URL: %s",
                url,
            )

            return url

        except Exception:
            logger.exception(
                "ERROR procesando imagen con Replicate"
            )
            raise
