# ComfyUI-Rect

Interactive rectangle tools for ComfyUI.  
Includes an interactive **Rect / Select** (marching-ants popup) plus **Rect / Crop**, **Rect / Mask**, and **Rect / Fill**.  
Outputs a reusable **RECT** object (`{x,y,w,h}`) and the four scalar values for compatibility with existing nodes.

---

## Features
- 🖱️ **Interactive selector**: draw/refine a box over your input image
- 🧱 **RECT type** + `x/y/w/h` ints for easy wiring
- ✂️ **Crop**, 🧪 **Mask** (feather/invert/combine), 🟩 **Fill/Outline** (color + opacity)
- 🚫 Bounds-safe, batch-safe, GPU/CPU friendly
- 🧩 Modular pack layout (easy to extend)

---

## Install

1. Copy the folder **`ComfyUI-Rect`** into:
