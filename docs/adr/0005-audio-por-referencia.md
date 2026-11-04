# El audio viaja por referencia en un object storage

El cliente sube el audio directo a un object storage (MinIO en local, S3 o R2 en producción) con una URL prefirmada que le da el Jobs API. Los mensajes solo llevan `audio_uri`. Así Redis no carga con varios MB por mensaje, y un Job que se reintenta no obliga a volver a subir el audio.
