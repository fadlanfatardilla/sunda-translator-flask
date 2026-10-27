const $ = (id) => document.getElementById(id);
const source = $("source"), go = $("go"), result = $("result"), copy = $("copy"), n = $("n");

function show(text, kind) {
  result.textContent = text;
  result.className = "result" + (kind ? " " + kind : "");
  copy.hidden = kind !== undefined && kind !== "";
}

async function translate() {
  const text = source.value.trim();
  if (!text) { show("Tulis kalimat dulu.", "error"); return; }
  go.disabled = true; go.textContent = "Sedang menerjemahkan...";
  try {
    const res = await fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) show(data.error || "Terjadi kesalahan.", "error");
    else show(data.translation, "");
  } catch (e) {
    show("Tidak bisa terhubung ke server. Pastikan aplikasi masih berjalan.", "error");
  } finally {
    go.disabled = false; go.textContent = "Translate";
  }
}

go.addEventListener("click", translate);
source.addEventListener("input", () => { n.textContent = source.value.length; });
source.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) translate(); });
document.querySelectorAll(".chip").forEach((c) =>
  c.addEventListener("click", () => { source.value = c.textContent; n.textContent = source.value.length; translate(); }));
copy.addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(result.textContent); copy.textContent = "Tersalin"; }
  catch { copy.textContent = "Gagal menyalin"; }
  setTimeout(() => (copy.textContent = "Salin hasil"), 1500);
});
