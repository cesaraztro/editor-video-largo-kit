"""Transcribe cada pieza del plan (audio del micrófono) con marcas por palabra y pista de muletillas → qa/palabras.json"""
import json, subprocess, sys, mlx_whisper
from pathlib import Path
W = Path(__file__).parent
PR = "Eh, este... o sea, te voy a, te voy a mostrar. Y en las, y en mi empresa. Pero tener todo, pero tener todo."
S = json.load(open(W / "plan2.json"))["segs"]; out = []
for i, s in enumerate(S):
    f = W / "qa" / "pz.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s['a']:.3f}", "-to", f"{s['b']:.3f}", "-i", str(W / "mic48_DeepFilterNet3.wav"),
                    "-ac", "1", "-ar", "16000", str(f)], check=True)
    r = mlx_whisper.transcribe(str(f), path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="es", initial_prompt=PR,
                               condition_on_previous_text=False, word_timestamps=True)
    ws = [{"w": w["word"].strip(), "a": round(s["a"] + w["start"], 2), "b": round(s["a"] + w["end"], 2)} for sg in r["segments"] for w in sg["words"]]
    out.append({"i": i, "a": s["a"], "b": s["b"], "palabras": ws})
json.dump(out, open(W / "qa" / "palabras.json", "w"), ensure_ascii=False, indent=1)
