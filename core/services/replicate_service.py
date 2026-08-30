import io
import logging

import replicate

from PIL import Image
from django.conf import settings


logger = logging.getLogger(__name__)


class ReplicateService:

    # Límite que nos está dando la GPU del modelo.
    MAX_PIXELS = 2_096_704

    @staticmethod
    def _prepare_image(image_file):
        """
        Prepara la imagen para Real-ESRGAN.

        Si la imagen está dentro del límite de píxeles,
        se envía sin modificar.

        Si supera el límite, se reduce proporcionalmente
        intentando aprovechar al máximo la capacidad disponible.
        """

        image_file.seek(0)

        image = Image.open(image_file)

        original_width, original_height = image.size
        original_pixels = (
            original_width * original_height
        )

        logger.info(
            "Original image: %sx%s (%s pixels)",
            original_width,
            original_height,
            original_pixels,
        )

        # No tocar imágenes que ya entran.
        if original_pixels <= ReplicateService.MAX_PIXELS:

            logger.info(
                "Image is within GPU limit. "
                "No resize required."
            )

            return image_file

        # Factor necesario para reducir la cantidad
        # de píxeles manteniendo la proporción.
        scale = (
            ReplicateService.MAX_PIXELS
            / original_pixels
        ) ** 0.5

        new_width = max(
            1,
            int(original_width * scale),
        )

        new_height = max(
            1,
            int(original_height * scale),
        )

        logger.info(
            "Resizing image: %sx%s -> %sx%s",
            original_width,
            original_height,
            new_width,
            new_height,
        )

        # LANCZOS es un filtro de alta calidad
        # especialmente bueno para reducir imágenes.
        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS,
        )

        logger.info(
            "Resized image: %sx%s (%s pixels)",
            new_width,
            new_height,
            new_width * new_height,
        )

        # Determinamos un formato apropiado.
        #
        # JPEG/WebP -> JPEG
        # PNG con transparencia -> PNG
        #
        # Para imágenes normales usamos JPEG con calidad alta.
        has_alpha = (
            image.mode in (
                "RGBA",
                "LA",
            )
            or (
                image.mode == "P"
                and "transparency" in image.info
            )
        )

        output = io.BytesIO()

        if has_alpha:

            if image.mode != "RGBA":
                image = image.convert("RGBA")

            image.save(
                output,
                format="PNG",
                optimize=True,
            )

            content_type = "image/png"
            extension = "png"

        else:

            if image.mode != "RGB":
                image = image.convert("RGB")

            image.save(
                output,
                format="JPEG",
                quality=95,
                optimize=True,
            )

            content_type = "image/jpeg"
            extension = "jpg"

        output.seek(0)

        # Le ponemos algunos atributos para que
        # Replicate pueda tratarlo como archivo.
        output.name = (
            f"enhance_input.{extension}"
        )

        logger.info(
            "Prepared image size: %s bytes",
            output.getbuffer().nbytes,
        )

        logger.info(
            "Prepared image format: %s",
            content_type,
        )

        return output

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
            "Filename: %s",
            getattr(
                image_file,
                "name",
                None,
            ),
        )

        logger.info(
            "Original size: %s bytes",
            getattr(
                image_file,
                "size",
                None,
            ),
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

            logger.error(
                "REPLICATE_API_TOKEN no está configurado"
            )

            raise Exception(
                "REPLICATE_API_TOKEN no configurado"
            )

        if scale not in [2, 4]:

            raise Exception(
                "La escala debe ser 2 o 4."
            )

        client = replicate.Client(
            api_token=token,
        )

        prepared_image = None

        try:

            prepared_image = (
                ReplicateService._prepare_image(
                    image_file
                )
            )

            logger.info(
                "Sending image to Replicate..."
            )

            output = client.run(
                "nightmareai/real-esrgan",
                input={
                    "image": prepared_image,
                    "scale": scale,
                    "face_enhance": face_enhance,
                },
            )

            logger.info(
                "Replicate response received."
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

        finally:

            # Liberamos el BytesIO si tuvimos que
            # redimensionar la imagen.
            if (
                prepared_image is not None
                and isinstance(
                    prepared_image,
                    io.BytesIO,
                )
            ):
                prepared_image.close()
