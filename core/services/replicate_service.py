
import replicate


class ReplicateService:

    @staticmethod
    def enhance_image(
        image_file,
        scale=2,
        face_enhance=False,
    ):
        """
        Mejora una imagen utilizando Real-ESRGAN.

        image_file:
            Django UploadedFile / archivo compatible.

        scale:
            2 o 4.

        face_enhance:
            Activa la mejora facial.
        """

        output = replicate.run(
            "nightmareai/real-esrgan",
            input={
                "image": image_file,
                "scale": scale,
                "face_enhance": face_enhance,
            },
        )

        return output
