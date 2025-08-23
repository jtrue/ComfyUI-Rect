# Rect / Fill — fill or outline a RECT region on IMAGE with color & opacity (optional feather)
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

def _gaussian_kernel1d(radius, sigma, device):
    xs = torch.arange(-radius, radius + 1, device=device, dtype=torch.float32)
    k = torch.exp(-(xs**2) / (2 * sigma * sigma))
    k /= k.sum().clamp_min(1e-8)
    return k

def _gaussian_blur(mask, radius):
    if radius < 1:
        return mask
    B, H, W = mask.shape
    device = mask.device
    sigma = max(0.5, radius / 2.5)
    k1d = _gaussian_kernel1d(radius, sigma, device)
    x = mask.unsqueeze(1)  # [B,1,H,W]
    kh = k1d.view(1, 1, 1, -1)
    kv = k1d.view(1, 1, -1, 1)
    x = F.pad(x, (radius, radius, 0, 0), mode="reflect")
    x = F.conv2d(x, kh)
    x = F.pad(x, (0, 0, radius, radius), mode="reflect")
    x = F.conv2d(x, kv)
    return x.squeeze(1).clamp(0.0, 1.0)

class RectFill:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rect": ("RECT",),
                "r": ("INT", {"default": 255, "min": 0, "max": 255}),
                "g": ("INT", {"default": 0,   "min": 0, "max": 255}),
                "b": ("INT", {"default": 0,   "min": 0, "max": 255}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
                "mode": ("STRING", {"default": "fill", "choices": ["fill", "outline"]}),
                "thickness": ("INT", {"default": 4, "min": 1, "max": 1024}),
                "feather": ("INT", {"default": 0, "min": 0, "max": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = "Rect"

    def run(self, image, rect, r, g, b, opacity, mode, thickness, feather):
        if not isinstance(image, torch.Tensor):
            raise ValueError("RectFill: expected torch.Tensor IMAGE")

        # Parse rect
        try:
            x = int(rect.get("x", 0)); y = int(rect.get("y", 0))
            w = int(rect.get("w", 1)); h = int(rect.get("h", 1))
        except Exception:
            x, y, w, h = 0, 0, 1, 1

        # Shapes
        if image.dim() == 4:
            B, H, W, C = int(image.shape[0]), int(image.shape[1]), int(image.shape[2]), int(image.shape[3])
            img = image
        elif image.dim() == 3:
            B, H, W, C = 1, int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
            img = image.unsqueeze(0)  # [1,H,W,C]
        else:
            raise ValueError(f"RectFill: unsupported IMAGE dims {tuple(image.shape)}")

        device = img.device
        x, y, w, h = _clamp_rect(x, y, w, h, W, H)

        # Build alpha mask in [B,H,W]
        alpha = torch.zeros((B, H, W), device=device, dtype=torch.float32)

        if mode == "fill":
            alpha[:, y:y+h, x:x+w] = 1.0
        else:  # outline
            # Outer rect
            alpha[:, y:y+h, x:x+w] = 1.0
            # Inner rect to subtract
            inner_w = max(0, w - 2 * thickness)
            inner_h = max(0, h - 2 * thickness)
            if inner_w > 0 and inner_h > 0:
                ix = x + thickness
                iy = y + thickness
                alpha[:, iy:iy+inner_h, ix:ix+inner_w] = 0.0

        # Feather (Gaussian blur)
        if feather > 0:
            alpha = _gaussian_blur(alpha, int(feather))

        # Apply opacity
        alpha = (alpha * float(opacity)).clamp(0.0, 1.0)

        # Color tensor [B,1,1,3] in 0..1
        color = torch.tensor([r, g, b], device=device, dtype=torch.float32) / 255.0
        color = color.view(1, 1, 1, 3).expand(B, 1, 1, 3)

        # Blend: out = alpha*color + (1-alpha)*img
        alpha4 = alpha.unsqueeze(-1)  # [B,H,W,1]
        out = (alpha4 * color) + ((1.0 - alpha4) * img)
        out = out.clamp(0.0, 1.0)

        if image.dim() == 3:
            out = out.squeeze(0)

        return (out,)

NODE_CLASS_MAPPINGS = {"RectFill": RectFill}
NODE_DISPLAY_NAME_MAPPINGS = {"RectFill": "Rect / Fill"}
