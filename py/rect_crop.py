# RectCrop node (display: "Rect / Crop")
# Crops an IMAGE to the given RECT (x,y,w,h in pixels).
import torch

def _image_size(image):
    if isinstance(image, torch.Tensor):
        if image.dim() == 4:  # [B,H,W,C]
            return int(image.shape[2]), int(image.shape[1])
        if image.dim() == 3:  # [H,W,C]
            return int(image.shape[1]), int(image.shape[0])
    return 512, 512

def _clamp_rect_for_crop(x, y, w, h, W, H):
    # Clamp top-left *inside* the image so slicing never returns empty.
    if W <= 0 or H <= 0:
        return 0, 0, 1, 1
    x = max(0, min(int(x), W - 1))
    y = max(0, min(int(y), H - 1))
    # Width/height must fit within the remaining bounds from (x,y)
    w = max(1, min(int(w), W - x))
    h = max(1, min(int(h), H - y))
    return x, y, w, h

class RectCrop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rect": ("RECT",),   # {"x":int,"y":int,"w":int,"h":int}
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = "Rect"

    def run(self, image, rect):
        # Extract rect safely
        try:
            x = int(rect.get("x", 0))
            y = int(rect.get("y", 0))
            w = int(rect.get("w", 1))
            h = int(rect.get("h", 1))
        except Exception:
            x, y, w, h = 0, 0, 1, 1

        W, H = _image_size(image)
        x, y, w, h = _clamp_rect_for_crop(x, y, w, h, W, H)

        if not isinstance(image, torch.Tensor):
            raise ValueError("RectCrop: expected torch.Tensor IMAGE")

        if image.dim() == 4:        # [B,H,W,C]
            cropped = image[:, y:y+h, x:x+w, :]
        elif image.dim() == 3:      # [H,W,C]
            cropped = image[y:y+h, x:x+w, :]
        else:
            raise ValueError(f"RectCrop: unsupported IMAGE dims {image.shape}")

        return (cropped,)

NODE_CLASS_MAPPINGS = {"RectCrop": RectCrop}
NODE_DISPLAY_NAME_MAPPINGS = {"RectCrop": "Rect / Crop"}
