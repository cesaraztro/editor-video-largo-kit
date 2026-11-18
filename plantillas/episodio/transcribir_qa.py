import sys, json, glob, mlx_whisper
PR = "Eh, este... o sea, te voy a, te voy a mostrar. Y, y entonces... la, la plataforma."
out = {}
for f in sorted(glob.glob(sys.argv[1] + "/*.wav")):
    r = mlx_whisper.transcribe(f, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="es",
                               initial_prompt=PR, condition_on_previous_text=False)
    out[f.rsplit("/", 1)[1][:-4]] = r["text"].strip()
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
