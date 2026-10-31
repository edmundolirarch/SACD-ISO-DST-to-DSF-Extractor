# SACD-ISO-DST-to-DSF-Extractor
🎵 Resumen de la Aplicación
Esta herramienta es una interfaz gráfica (GUI) moderna, ligera y portátil diseñada para extraer exclusivamente la capa estéreo de archivos SACD ISO/DST y convertirlos directamente a formato DSF sin pérdida (bit-perfect).

Fue pensada para usuarios de reproductores modernos (como la línea HiBy, FiiO, Astell&Kern, Shanling) que necesitan los archivos listos para su lectura con metadatos perfectos. No comprime, no pasa por PCM y no altera la muestra DSD; simplemente desenvuelve el archivo ISO, extrae la pista estéreo, inyecta las etiquetas ID3v2 y las carátulas, y te lo entrega listo para copiar a tu tarjeta MicroSD u otro dispositivo de almacenamiento.

Características Principales:

100% Portátil: Un único archivo .exe. Sin instalaciones, sin dependencias.

Extracción Bit-Perfect: Uso del motor nativo (sacd_extract) de forma invisible (-s -c). Mantiene la integridad DSD pura.

Búsqueda Online Integrada: Conectado a la base de datos de MusicBrainz. Escribe el artista y el álbum, y la app llena los nombres de las pistas automáticamente.

Control Total de Metadatos: Inyección nativa de etiquetas (Artista, Álbum, Título y Número de pista) en la cabecera ID3 del archivo .dsf.

Orden Cronológico Perfecto: Genera los archivos bajo el formato físico 01 - Título.dsf e inyecta el metadato interno TRCK, garantizando que tu DAP reproduzca el álbum en el orden original.

Carátulas de Alta Calidad: Soporta carga manual de portadas locales para incrustarlas directamente dentro de cada archivo de audio.

🛠️ Documentación Técnica y Flujo de Trabajo
La arquitectura de la aplicación combina la eficiencia del procesamiento binario en C con la flexibilidad del etiquetado moderno en Python, manejado a través de múltiples hilos para una experiencia fluida.

1. Requisitos y Compatibilidad
Sistema Operativo: Windows 10 / Windows 11 (64-bits).

Formatos de Entrada: Imágenes de disco SACD (.iso) en DST.

Formato de Salida: Archivos DSD (.dsf) de la capa estéreo (2.0).

2. Flujo Interno de la Aplicación (El "Backend" Oculto)
Escaneo Rápido (TOC): Al cargar un ISO, la app ejecuta un escaneo silencioso (sacd_extract -i) para leer la tabla de contenidos. Si el ISO carece de metadatos internos por ser un ripeo temprano, se generan pistas genéricas de forma temporal.

Extracción al Buffer Temporal: Para evitar problemas de permisos de escritura y renombrado en Windows, la aplicación extrae el disco completo en una carpeta temporal oculta (tempfile.TemporaryDirectory).

Procesamiento Asíncrono (Multithreading): La interfaz visual (CustomTkinter) opera en el hilo principal, mientras que la extracción y la inyección de metadatos corren en un hilo secundario. Esto evita que la ventana se congele (el temido "No Responde") y permite actualizar las barras de progreso leyendo el stdout del binario en tiempo real.

Renombrado y Mudanza: Una vez el archivo base está en el buffer temporal, el motor de Python lo renombra aplicando una limpieza de caracteres especiales de Windows (\/*?:"<>|), aplicando el formato 00 - Nombre de Pista.dsf, y lo mueve a la ruta de destino elegida.

3. Sistema de Etiquetado Nativo (Mutagen)
A diferencia de otros scripts que requieren herramientas de terceros como Mp3tag, esta aplicación integra la librería mutagen.

Una vez el archivo DSD físico está en su destino, se abre la cabecera.

Se inyectan las etiquetas TIT2 (Título), TPE1 (Artista), TALB (Álbum) y TRCK (Número de Pista).

Se incrusta el bloque APIC (Portada) codificado en base64 con su respectivo MIME type, asegurando que los reproductores MTouch OS y Android lean la carátula instantáneamente.

4. Prevención de Errores

Control de Conflictos: Antes de iniciar cualquier proceso, el sistema simula el renombrado final. Si detecta que un archivo con ese nombre ya existe en la carpeta destino, cancela la operación entera antes de comenzar, evitando sobreescrituras accidentales de horas de trabajo.

Edición Dinámica: Si un ISO está mal ripeado (como los primeros ripeos de PS3) y se detectan menos pistas de las reales o la tabla TOC está corrupta, puedes utilizar los controles manuales de la UI (+ Añadir Pista / - Quitar Pista) para ajustar la tabla a la realidad del disco antes de extraer.

5. Notas para Desarrolladores / Compilación
Si deseas revisar o modificar el código fuente original en Python, la aplicación está construida sobre las siguientes librerías:

customtkinter (Interfaz Gráfica)

mutagen (Inyección ID3 para DSD)

pyinstaller (Empaquetado)

El motor binario sacd_extract.exe original se incluye como recurso incrustado mediante el comando:
pyinstaller --noconsole --onefile --add-data "sacd_extract.exe;." script.py

## 👤 Autor
Desarrollado por Gianfranco Lira Arbe - Lima, Perú
