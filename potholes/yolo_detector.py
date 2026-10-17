from pathlib import Path
from django.conf import settings
from ultralytics import YOLO
from PIL import Image
import io

MODEL_PATH = Path(settings.BASE_DIR) / "models" / "best.pt"

model = YOLO(str(MODEL_PATH))


def detect_pothole(image_path, threshold=0.10):
    results = model.predict(
        source=str(image_path),
        conf=threshold,
        verbose=False,
    )

    result = results[0]

    best_confidence = 0.0
    detected_label = "no_pothole"

    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            if class_id == 0 and confidence > best_confidence:
                best_confidence = confidence
                detected_label = "pothole"

    is_pothole = detected_label == "pothole"

    # Generate annotated image with YOLO bounding boxes and labels
    annotated_array = result.plot()

    # YOLO plot output is BGR; convert it to RGB
    annotated_image = Image.fromarray(
        annotated_array[:, :, ::-1]
    )

    # Encode the annotated image as JPEG in memory
    annotated_file = io.BytesIO()

    annotated_image.save(
        annotated_file,
        format="JPEG",
        quality=90,
    )

    annotated_file.seek(0)

    return {
        "is_pothole": is_pothole,
        "label": detected_label,
        "confidence": best_confidence,
        "annotated_image": annotated_file,
    }
