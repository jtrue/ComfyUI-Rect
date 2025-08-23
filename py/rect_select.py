# RectSelect node (display: "Rect / Select")
import torch

def _image_size(image):
    if isinstance(image, torch.Tensor):
        if image.dim() == 4:  # [B,H,W,C]
            return int(image.shape[2]), int(image.shape[1])
        if image.dim() == 3:  # [H,W,C]
            return int(image.shape[1]), int(image.shape[0])
    return 512, 512

def _clamp_rect(x, y, w, h, W, H):
    x = max(0, min(int(x), max(0, W)))
    y = max(0, min(int(y), max(0, H)))
    w = max(1, int(w))
    h = max(1, int(h))
    if x + w > W: w = max(1, W - x)
    if y + h > H: h = max(1, H - y)
    return x, y, w, h

class RectSelect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0}),
                "y": ("INT", {"default": 0, "min": 0}),
                "w": ("INT", {"default": 256, "min": 1}),
                "h": ("INT", {"default": 256, "min": 1}),
            }
        }

    # Output a RECT object and the four ints (compat with existing crop nodes)
    RETURN_TYPES = ("RECT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("rect", "x", "y", "w", "h")
    FUNCTION = "run"
    CATEGORY = "Rect"

    def run(self, image, x, y, w, h):
        W, H = _image_size(image)
        x, y, w, h = _clamp_rect(x, y, w, h, W, H)
        rect = {"x": x, "y": y, "w": w, "h": h}
        return (rect, x, y, w, h)

NODE_CLASS_MAPPINGS = {"RectSelect": RectSelect}
NODE_DISPLAY_NAME_MAPPINGS = {"RectSelect": "Rect / Select"}
