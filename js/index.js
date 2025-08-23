// ComfyUI-Rect front-end (Rect / Select) — marching ants, image-required, auto-prefill
import { app } from "../../scripts/app.js";

function setWidget(node, name, value) {
  const w = node.widgets?.find(w => w.name === name);
  if (w) {
    w.value = value;
    node.onWidgetChanged?.(name, value, w);
  }
  node.properties[name] = value;
  node.setDirtyCanvas?.(true, true);
}

function toast(text, ms = 1800) {
  const div = document.createElement("div");
  Object.assign(div.style, {
    position: "fixed", right: "16px", bottom: "16px",
    background: "rgba(20,20,20,.9)", color: "#eee",
    padding: "10px 12px", borderRadius: "10px",
    zIndex: 10000, font: "12px/1.3 system-ui, sans-serif",
    boxShadow: "0 6px 16px rgba(0,0,0,.35)"
  });
  div.textContent = text;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), ms);
}

function upstreamFilenameFromImageInput(node) {
  const idx = node.inputs?.findIndex(i => i.name === "image");
  if (idx == null || idx < 0) return null;
  const linkId = node.inputs[idx]?.link;
  if (!linkId) return null;
  const link = app.graph.links?.[linkId];
  const upstream = link ? app.graph._nodes_by_id?.[link.origin_id] : null;
  const w = upstream?.widgets?.find(w => w.name === "image" && typeof w.value === "string" && w.value.length);
  return w ? String(w.value) : null;
}

function buildInputViewURL(nameOrPath) {
  let p = String(nameOrPath).replace(/\\/g, "/");
  const parts = p.split("/");
  const file = parts.pop();
  const subfolder = parts.join("/");
  const ext = (file.split(".").pop() || "png").toLowerCase();
  const format = ext === "jpg" || ext === "jpeg" ? "jpeg" : "png";
  const u = new URL(`${location.origin}/view`);
  u.searchParams.set("type", "input");
  u.searchParams.set("filename", file);
  u.searchParams.set("subfolder", subfolder);
  u.searchParams.set("format", format);
  return u.toString();
}

function openRectSelect(node) {
  const upstreamName = upstreamFilenameFromImageInput(node);
  if (!upstreamName) { toast("Rect / Select: connect an image to the 'image' input."); return; }
  const upstreamURL = buildInputViewURL(upstreamName);

  // Overlay & modal
  const overlay = document.createElement("div");
  Object.assign(overlay.style, {
    position: "fixed", inset: "0", background: "rgba(0,0,0,0.6)",
    zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center"
  });

  const modal = document.createElement("div");
  Object.assign(modal.style, {
    background: "#111", color: "#eee", padding: "16px", borderRadius: "12px",
    width: "min(92vw, 1100px)", maxHeight: "90vh",
    display: "grid", gridTemplateRows: "auto 1fr auto", gap: "12px",
    boxShadow: "0 10px 30px rgba(0,0,0,0.5)"
  });
  overlay.appendChild(modal);

  // Header
  const header = document.createElement("div");
  Object.assign(header.style, { display: "flex", justifyContent: "space-between", alignItems: "center" });
  header.innerHTML = `<div style="font-weight:600">Rect / Select</div>`;
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "Close";
  closeBtn.onclick = () => document.body.removeChild(overlay);
  header.appendChild(closeBtn);
  modal.appendChild(header);

  // Canvas area
  const area = document.createElement("div");
  Object.assign(area.style, { overflow: "auto", background: "#222", padding: "8px" });
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  area.appendChild(canvas);
  modal.appendChild(area);

  // Footer (coords left, Apply right)
  const footer = document.createElement("div");
  Object.assign(footer.style, { display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" });

  const coords = document.createElement("div");
  Object.assign(coords.style, { color: "#aaa", fontStyle: "italic", fontSize: "12px", minHeight: "1em" });

  const spacer = document.createElement("div");
  spacer.style.flex = "1";

  const applyBtn = document.createElement("button");
  applyBtn.textContent = "Apply Rect";
  applyBtn.disabled = true;
  Object.assign(applyBtn.style, { padding: "10px 14px", fontWeight: "600", borderRadius: "8px", border: "none", cursor: "pointer" });

  footer.append(coords, spacer, applyBtn);
  modal.appendChild(footer);

  // State
  let img = new Image(), imgLoaded = false;
  let dragging = false, sx = 0, sy = 0, cx = 0, cy = 0;
  let antsOffset = 0;

  // Helpers
  function clampRect(x, y, w, h, W, H) {
    x = Math.max(0, Math.min(x, W));
    y = Math.max(0, Math.min(y, H));
    w = Math.max(1, Math.min(w, W));
    h = Math.max(1, Math.min(h, H));
    if (x + w > W) w = Math.max(1, W - x);
    if (y + h > H) h = Math.max(1, H - y);
    return [x, y, w, h];
  }

  function setSelectionFromNode() {
    if (!imgLoaded) return;
    const W = img.naturalWidth, H = img.naturalHeight;
    let nx = Number(node.properties?.x ?? 0);
    let ny = Number(node.properties?.y ?? 0);
    let nw = Number(node.properties?.w ?? Math.floor(W / 2));
    let nh = Number(node.properties?.h ?? Math.floor(H / 2));
    [nx, ny, nw, nh] = clampRect(nx, ny, nw, nh, W, H);
    const sxScale = canvas.width / W;
    const syScale = canvas.height / H;
    sx = Math.round(nx * sxScale); sy = Math.round(ny * syScale);
    cx = Math.round((nx + nw) * sxScale); cy = Math.round((ny + nh) * syScale);
    draw();
  }

  function fitToViewport() {
    if (!imgLoaded) return;
    const maxW = Math.min(window.innerWidth * 0.88, 1600);
    const maxH = Math.min(window.innerHeight * 0.65, 900);
    const scale = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1);
    canvas.width  = Math.max(2, Math.floor(img.naturalWidth  * scale));
    canvas.height = Math.max(2, Math.floor(img.naturalHeight * scale));
    setSelectionFromNode();
  }

  function draw() {
    ctx.fillStyle = "#333"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (imgLoaded) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const x = Math.min(sx, cx), y = Math.min(sy, cy);
    const w = Math.abs(cx - sx), h = Math.abs(cy - sy);
    if (w > 0 && h > 0) {
      const seg = 8;
      ctx.lineWidth = 2;
      ctx.setLineDash([seg, seg]);
      ctx.lineDashOffset = -antsOffset; ctx.strokeStyle = "#fff"; ctx.strokeRect(x, y, w, h);
      ctx.lineDashOffset = seg - antsOffset; ctx.strokeStyle = "#000"; ctx.strokeRect(x, y, w, h);
      coords.textContent = `x=${x}, y=${y}, w=${w}, h=${h}`;
    } else {
      coords.textContent = imgLoaded ? "Drag to draw a rectangle." : "";
    }
  }

  function animate() {
    antsOffset = (antsOffset + 1) % 16;
    draw();
    if (document.body.contains(overlay)) requestAnimationFrame(animate);
  }

  function loadFromURL(url) {
    img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => { imgLoaded = true; applyBtn.disabled = false; fitToViewport(); };
    img.onerror = () => { toast("Rect / Select: could not load upstream image."); };
    img.src = url;
  }

  // Interactions
  canvas.addEventListener("mousedown", (e) => {
    if (!imgLoaded) return;
    const r = canvas.getBoundingClientRect();
    sx = cx = e.clientX - r.left; sy = cy = e.clientY - r.top; dragging = true; draw();
  });
  canvas.addEventListener("mousemove", (e) => {
    if (!dragging || !imgLoaded) return;
    const r = canvas.getBoundingClientRect();
    cx = e.clientX - r.left; cy = e.clientY - r.top; draw();
  });
  window.addEventListener("mouseup", () => { if (dragging) { dragging = false; draw(); } });
  window.addEventListener("resize", fitToViewport);

  applyBtn.onclick = () => {
    if (!imgLoaded) return;
    const scaleX = img.naturalWidth  / canvas.width;
    const scaleY = img.naturalHeight / canvas.height;
    const x = Math.round(Math.min(sx, cx) * scaleX);
    const y = Math.round(Math.min(sy, cy) * scaleY);
    const w = Math.round(Math.abs(cx - sx) * scaleX);
    const h = Math.round(Math.abs(cy - sy) * scaleY);
    if (w < 1 || h < 1) { toast("Draw a rectangle first."); return; }
    setWidget(node, "x", x); setWidget(node, "y", y);
    setWidget(node, "w", w); setWidget(node, "h", h);
    setTimeout(() => document.body.contains(overlay) && document.body.removeChild(overlay), 250);
  };

  document.body.appendChild(overlay);
  requestAnimationFrame(animate);
  loadFromURL(upstreamURL);
}

// Register: attach button to RectSelect nodes
app.registerExtension({
  name: "ComfyUI-Rect",
  nodeCreated(node) {
    if (node?.comfyClass !== "RectSelect") return;
    if (node.widgets?.some(w => w.__rect_btn)) return;
    const btn = node.addWidget("button", "Open Rect / Select", "open", () => openRectSelect(node));
    btn.__rect_btn = true;

    node.properties ??= {};
    node.properties.x ??= 0; node.properties.y ??= 0;
    node.properties.w ??= 256; node.properties.h ??= 256;

    console.log("[Rect] button attached to node", node.id);
  },
});
