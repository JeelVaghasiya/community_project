# P1: Computer Vision Engineer

**Branch:** `p1/cv`  
**Folder Ownership:** `cv/`, `docs/cv_eval_report.md`  
**Main Language:** Python  

## Stack
- PyTorch & Hugging Face Transformers (`SegFormer-b0`)
- `ultralytics` (`YOLOv8-pose`)
- OpenCV (`cv2`) & Albumentations

## Key Deliverables & Shared Contract
- `cv/dataset.py`: Dataset loader & augmentations
- `cv/train_seg.py`: SegFormer-b0 water fine-tuning
- `cv/depth.py`: Depth heuristic using YOLOv8-pose keypoints (ankle/knee)
- `cv/analyze.py`: Main `analyze(image_path) -> dict` returning the contract:
  ```json
  {
    "image_id": "img_007",
    "flooded": true,
    "water_area_pct": 34.2,
    "depth_class": "knee",
    "confidence": 0.81,
    "annotated_image": "outputs/img_007_annot.png"
  }
  ```
  `depth_class` options: `none`, `ankle`, `knee`, `thigh`, `unknown`.
