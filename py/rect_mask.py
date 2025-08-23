# Rect / Mask — build a MASK from a RECT, with optional feather/invert/combine
import math
import torch
import torch.nn.functional as F

def _image_size(image):
    if isinstance(image, torch.Tensor):
        if image.dim() == 4:  # [B,H,W,C]
            return int(image.shape[2]), int(image.shape[1])
        if image.dim() == 3:  # [H,W,C]
            return int(image.shape[1]), int(image.shape[0])
    return 512, 512

def _clamp_rect(x, y, w, h, W, H):
    x = max(0, min(int(x), max(0, W - 1)))
    y = max(0, min(int(y), max(0, H - 1)))
    w = max(1, min(int(w), W - x))
    h = max(1, min(int(h), H - y))
    return x, y, w, h

def _ensure_mask_shape(mask, B, H, W, device):
    # Accept [H,W], [B,H,W], or [B,1,H,1] quirky shapes from some packs
    if mask is None:
        return None
    if mask.dim() == 2:
        mask = mask.unsqueeze(0)  # [1,H,W]
    if mask.dim() == 4 and mask.shape[1] == 1 and mask.shape[3] == 1:
        mask = mask[:, 0, :, :]  # [B,H,W]
    if mask.dim() != 3:
        raise ValueError(f"RectMask: unsupported mask shape {tuple(mask.shape)}")
    # Broadcast or clamp batch as needed
    if mask.shape[0] == 1 and B > 1:
        mask = mask.expand(B, H, W).clone()
    elif mask.shape[0] != B:
        # If sizes mismatch, just take first and broadcast
        mask = mask[:1].expand(B, H, W).clone()
    # Resize if spatial size mismatches
    if (mask.shape[1] != H) or (mask.shape[2] != W):
        mask = F.interpolate(mask.unsqueeze(1), size=(H, W), mode="bilinear", align_corners=False).squeeze(1)
    return mask.to(device=device, dtype=torch.float32).clamp(0.0, 1.0)

def _gaussian_kernel1d(radius, sigma, device):
    # radius: pixels; kernel size = 2*radius+1
    xs = torch.arange(-radius, radius + 1, device=device, dtype=torch.float32)
    k = torch.exp(-(xs**2) / (2 * sigma * sigma))
    k /= k.sum().clamp_min(1e-8)
    return k

def _gaussian_blur(mask, radius):
    # mask: [B,H,W], radius >= 1
    if radius < 1:
        return mask
    B, H, W = mask.shape
    device = mask.device
    sigma = max(0.5, radius / 2.5)
    k1d = _gaussian_kernel1d(radius, sigma, device)
    # separable blur: first horizontal, then vertical
    x = mask.unsqueeze(1)  # [B,1,H,W]
    kh = k1d.view(1, 1, 1, -1)
    kv = k1d.view(1, 1, -1, 1)
    x = F.pad(x, (radius, radius, 0, 0), mode="reflect")
    x = F.conv2d(x, kh)
    x = F.pad(x, (0, 0, radius, radius), mode="reflect")
    x = F.conv2d(x, kv)
    return x.squeeze(1).clamp(0.0, 1.0)

class RectMask:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rect": ("RECT",),  # {"x","y","w","h"}
                "feather": ("INT", {"default": 0, "min": 0, "max": 256}),
                "invert": ("BOOLEAN", {"default": False}),
                "combine": ("STRING", {"default": "replace",
                                       "choices": ["replace", "union", "intersect", "subtract", "multiply"]}),
            },
            "optional": {
                "existing_mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = "Rect"

    def run(self, image, rect, feather, invert, combine, existing_mask=None):
        if not isinstance(image, torch.Tensor):
            raise ValueError("RectMask: expected torch.Tensor IMAGE")

        # Parse rect
        try:
            x = int(rect.get("x", 0)); y = int(rect.get("y", 0))
            w = int(rect.get("w", 1)); h = int(rect.get("h", 1))
        except Exception:
            x, y, w, h = 0, 0, 1, 1

        # Get sizes and clamp rect
        if image.dim() == 4:
            B, H, W, C = int(image.shape[0]), int(image.shape[1]), int(image.shape[2]), int(image.shape[3])
        elif image.dim() == 3:
            B, H, W, C = 1, int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
        else:
            raise ValueError(f"RectMask: unsupported IMAGE dims {tuple(image.shape)}")

        device = image.device
        x, y, w, h = _clamp_rect(x, y, w, h, W, H)

        # Build binary rect mask
        mask = torch.zeros((B, H, W), device=device, dtype=torch.float32)
        mask[:, y:y+h, x:x+w] = 1.0

        # Feather (Gaussian)
        if feather > 0:
            radius = int(feather)
            mask = _gaussian_blur(mask, radius)

        # Invert
        if invert:
            mask = 1.0 - mask

        # Combine with existing_mask
        if existing_mask is not None:
            em = _ensure_mask_shape(existing_mask, B, H, W, device)
            if combine == "replace":
                mask = mask
            elif combine == "union":
                mask = torch.maximum(em, mask)
            elif combine == "intersect":
                mask = torch.minimum(em, mask)
            elif combine == "subtract":
                mask = (em - mask).clamp(0.0, 1.0)
            elif combine == "multiply":
                mask = (em * mask).clamp(0.0, 1.0)

        return (mask,)

NODE_CLASS_MAPPINGS = {"RectMask": RectMask}
NODE_DISPLAY_NAME_MAPPINGS = {"RectMask": "Rect / Mask"}
