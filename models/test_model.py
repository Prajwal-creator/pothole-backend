
from ultralytics import YOLO

model = YOLO(r"C:\project\backend\models\best.pt")

image_path = r"C:\project\backend\media\image.jpg"

results = model.predict(
    source=image_path,
    conf=0.10,
    save=True,
    verbose=False
)

result = results[0]
pothole_detected = False

for box in result.boxes:
    class_id = int(box.cls[0].item())
    confidence = float(box.conf[0].item())
    label = result.names[class_id]

    print(f"Detected: {label}, Confidence: {confidence:.2f}")

    if class_id == 0:
        pothole_detected = True

print("\nPOTHOLE DETECTED:", pothole_detected)
print("Classes:", model.names)
print("Annotated image saved in runs/detect/predict/")
