import pathlib

f = pathlib.Path("gmi_erp/settings.py")
t = f.read_text(encoding="utf-8")

needle = 'django.contrib.messages.context_processors.messages",'
replacement = (
    'django.contrib.messages.context_processors.messages",\n'
    '                "core.context_processors.gmi_context",'
)

if "gmi_context" not in t:
    t = t.replace(needle, replacement, 1)
    f.write_text(t, encoding="utf-8")
    print("Patched settings.py with gmi_context")
else:
    print("gmi_context already present")
